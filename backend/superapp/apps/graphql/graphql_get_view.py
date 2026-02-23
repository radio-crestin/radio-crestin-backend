"""
GraphQL POST-to-GET redirect view for CDN caching.

When a POST query hits /graphql, this view redirects it to a GET URL:
  /graphql?query=...&variables=...&timestamp=<rounded>

GET requests with a query param are executed directly and return JSON
with Cache-Control headers parsed from the @cache_control directive.

Mutations are NOT redirected - they execute via POST as normal.

Configuration (via Django settings):
  GRAPHQL_GET_REDIRECT_ENABLED = True/False  (default: True)
  GRAPHQL_GET_REDIRECT_TIMESTAMP_ROUND_SECONDS = 10  (default: 10)
"""

import json
import logging
import re
import urllib.parse
from collections import OrderedDict

from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.utils import timezone
from django.views import View
from strawberry.django.context import StrawberryDjangoContext
from strawberry.django.views import GraphQLView

from superapp.apps.graphql.schema import schema


logger = logging.getLogger(__name__)

_MUTATION_RE = re.compile(r'^\s*mutation\b', re.IGNORECASE)

# Matches @cache_control(...) directive on a GraphQL operation
_CACHE_CONTROL_DIRECTIVE_RE = re.compile(
    r'@cache_control\s*\(([^)]+)\)',
    re.IGNORECASE,
)

# Matches individual arguments like max_age: 30 or public: true
_DIRECTIVE_ARG_RE = re.compile(
    r'(\w+)\s*:\s*(\w+)',
)

# Map from @cache_control arg names to Cache-Control header directives
_CACHE_CONTROL_HEADER_MAP = {
    'max_age': ('max-age', 'int'),
    's_maxage': ('s-maxage', 'int'),
    'stale_while_revalidate': ('stale-while-revalidate', 'int'),
    'stale_if_error': ('stale-if-error', 'int'),
    'max_stale': ('max-stale', 'int'),
    'public': ('public', 'bool'),
    'private': ('private', 'bool'),
    'no_cache': ('no-cache', 'bool'),
    'immutable': ('immutable', 'bool'),
}


def _is_mutation(query: str) -> bool:
    """Check if a GraphQL query string is a mutation."""
    return bool(_MUTATION_RE.match(query))


def _parse_cache_control_header(query: str) -> str:
    """Parse @cache_control directive from a GraphQL query and return a Cache-Control header value.

    Example:
        query GetStations @cache_control(max_age: 30, public: true) { ... }
        -> "public, max-age=30"
    """
    match = _CACHE_CONTROL_DIRECTIVE_RE.search(query)
    if not match:
        return ''

    args_str = match.group(1)
    parts = []

    for arg_match in _DIRECTIVE_ARG_RE.finditer(args_str):
        name = arg_match.group(1)
        value = arg_match.group(2)

        mapping = _CACHE_CONTROL_HEADER_MAP.get(name)
        if not mapping:
            continue

        header_name, value_type = mapping

        if value_type == 'bool':
            if value.lower() in ('true', '1', 'yes'):
                parts.append(header_name)
        elif value_type == 'int':
            try:
                parts.append(f'{header_name}={int(value)}')
            except ValueError:
                pass

    return ', '.join(parts)


class GraphQLWithGetRedirectView(View):
    """GraphQL view that redirects POST queries to GET for CDN caching.

    POST /graphql (query) -> 302 GET /graphql?query=...&variables=...&timestamp=<rounded>
    POST /graphql (mutation) -> execute normally via Strawberry
    GET /graphql?query=... -> execute query, return JSON with Cache-Control headers
    GET /graphql (no query) -> Strawberry handles normally (GraphiQL IDE)
    """

    _strawberry_view_func = None

    @classmethod
    def _get_strawberry_view(cls):
        if cls._strawberry_view_func is None:
            cls._strawberry_view_func = GraphQLView.as_view(schema=schema)
        return cls._strawberry_view_func

    def dispatch(self, request, *args, **kwargs):
        # POST queries -> redirect to GET for CDN caching
        if request.method == 'POST' and self._should_redirect(request):
            return self._redirect_post_to_get(request)

        # GET with query param -> execute directly, return JSON with cache headers
        if request.method == 'GET' and 'query' in request.GET:
            return self._execute_get_query(request)

        # Everything else (GraphiQL IDE, OPTIONS, POST mutations) -> Strawberry
        return self._get_strawberry_view()(request, *args, **kwargs)

    def _should_redirect(self, request):
        """Check if this POST request should be redirected to GET."""
        enabled = getattr(settings, 'GRAPHQL_GET_REDIRECT_ENABLED', True)
        if not enabled:
            return False

        try:
            body = json.loads(request.body)
            query = body.get('query', '')
        except (json.JSONDecodeError, UnicodeDecodeError):
            return False

        if _is_mutation(query):
            return False

        return True

    def _redirect_post_to_get(self, request):
        """Build GET redirect URL from POST body and redirect."""
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self._get_strawberry_view()(request)

        query = body.get('query', '')
        variables = body.get('variables') or {}
        operation_name = body.get('operationName')

        # Minify query (collapse whitespace for shorter URLs)
        query = ' '.join(query.split())

        # Build URL params (ordered for consistent CDN cache keys)
        params = OrderedDict()
        params['query'] = query
        if variables:
            params['variables'] = json.dumps(variables, sort_keys=True, separators=(',', ':'))
        if operation_name:
            params['operationName'] = operation_name

        # Add rounded timestamp for cache busting
        round_seconds = getattr(settings, 'GRAPHQL_GET_REDIRECT_TIMESTAMP_ROUND_SECONDS', 10)
        if round_seconds > 0:
            current_ts = timezone.now().timestamp()
            rounded = int(current_ts // round_seconds) * round_seconds
            params['timestamp'] = str(rounded)

        query_string = urllib.parse.urlencode(params)
        redirect_url = f"{request.path}?{query_string}"

        return HttpResponseRedirect(redirect_url)

    def _execute_get_query(self, request):
        """Execute a GraphQL GET query and return JSON with Cache-Control headers."""
        query = request.GET.get('query', '')
        if not query:
            return JsonResponse({"error": "Missing 'query' parameter"}, status=400)

        # Parse variables
        variables = {}
        variables_param = request.GET.get('variables')
        if variables_param:
            try:
                variables = json.loads(variables_param)
            except (json.JSONDecodeError, TypeError):
                return JsonResponse(
                    {"error": "Invalid 'variables' parameter - must be valid JSON"},
                    status=400,
                )

        operation_name = request.GET.get('operationName')

        try:
            # Execute via Strawberry schema (runs all extensions including @cached)
            response_obj = HttpResponse()
            context = StrawberryDjangoContext(request=request, response=response_obj)

            result = schema.execute_sync(
                query,
                variable_values=variables if variables else None,
                operation_name=operation_name,
                context_value=context,
            )

            response_data = {"data": result.data}
            if result.errors:
                response_data["errors"] = [
                    {"message": str(error)} for error in result.errors
                ]

            response = JsonResponse(response_data)

            # Set Cache-Control: first check if the extension set it on context.response,
            # then fall back to parsing the @cache_control directive from the query.
            cc_from_ext = response_obj.get('Cache-Control')
            if cc_from_ext:
                response['Cache-Control'] = cc_from_ext
            else:
                cc_from_query = _parse_cache_control_header(query)
                if cc_from_query:
                    response['Cache-Control'] = cc_from_query

            # CORS headers
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Methods'] = 'GET, HEAD, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            response['Access-Control-Max-Age'] = '86400'
            response['Vary'] = 'Accept-Encoding'

            return response

        except Exception as e:
            logger.error(f"Error in GraphQL GET query execution: {e}")
            return JsonResponse(
                {"errors": [{"message": f"Internal server error: {str(e)}"}]},
                status=500,
            )
