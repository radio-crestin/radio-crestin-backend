import asyncio
import os
import logging

from asgiref.sync import iscoroutinefunction, markcoroutinefunction
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import JsonResponse

logger = logging.getLogger(__name__)


class GraphQlSuperuserApiAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.api_key = os.getenv('ADMIN_GRAPHQL_SUPERUSER_API_KEY')
        self._superuser = None  # Cache the superuser to avoid repeated DB queries

    def __call__(self, request):
        # The authentication is disabled for now
        if request.path == '/graphql' or request.path == '/v1/graphql' or request.path == '/v2/graphql':
            auth_header = request.headers.get('Authorization')
            if not request.user.is_authenticated:
                if auth_header and self.api_key and auth_header.endswith(self.api_key):
                    # Lazy load superuser only when needed
                    if self._superuser is None:
                        User = get_user_model()
                        try:
                            self._superuser = User.objects.filter(is_superuser=True).first()
                        except Exception as e:
                            logger.warning(f"Could not fetch superuser: {e}")
                    
                    if self._superuser:
                        request.user = self._superuser

        response = self.get_response(request)
        return response


CREDENTIAL_HEADERS = ('Authorization', 'X-Streaming-Api-Key', 'X-Api-Key')


def carries_credentials(request):
    """True when the response may depend on who is asking.

    Checks only what the request carries (no database lookup, so it is safe in
    async code): a logged-out browser with a stale session cookie also counts,
    which costs it the shared cache, never someone else their data.
    """
    if settings.SESSION_COOKIE_NAME in request.COOKIES:
        return True
    return any(request.headers.get(name) for name in CREDENTIAL_HEADERS)


def is_shared_cacheable(response):
    """True when a CDN or other shared cache may store this response."""
    cache_control = response.get('Cache-Control', '').lower()
    return 'public' in cache_control or 's-maxage' in cache_control


class PublicCacheHeadersMiddleware:
    """
    Make publicly-cacheable responses actually cacheable at the edge.

    Django appends to Vary during *response* processing, after the view has run:
    LocaleMiddleware always adds `Accept-Language`, and SessionMiddleware adds
    `Cookie` whenever the session is touched. Cloudflare declines to cache any
    response whose Vary names anything beyond Accept-Encoding, so those two
    additions silently defeated the `Cache-Control: public, max-age=..., immutable`
    that endpoints like /api/v1/stations set — every timestamp bucket travelled
    to the origin instead of being served from the edge.

    Registered first in MIDDLEWARE so its response phase runs last, after the
    middlewares that add Vary. It only rewrites responses a view opted in by
    setting `_public_cacheable`, so authenticated and per-user views keep their
    correct Vary headers.

    It is also the last line of defence against sharing one user's response
    with another: a request that carries credentials (a session cookie, an
    Authorization or API-key header) never gets a shared-cacheable response,
    whatever the view asked for. GraphQL GET takes its Cache-Control from the
    query text, which the caller writes, so the view alone cannot promise that.

    Supports both sync and async (ASGI) request paths.
    """

    sync_capable = True
    async_capable = True

    def __init__(self, get_response):
        self.get_response = get_response
        if iscoroutinefunction(self.get_response):
            markcoroutinefunction(self)

    def __call__(self, request):
        if iscoroutinefunction(self.get_response):
            return self.__acall__(request)
        return self._patch(request, self.get_response(request))

    async def __acall__(self, request):
        return self._patch(request, await self.get_response(request))

    @staticmethod
    def _patch(request, response):
        if is_shared_cacheable(response) and carries_credentials(request):
            response['Cache-Control'] = 'private, no-store'
            response._public_cacheable = False
            return response

        if not getattr(response, '_public_cacheable', False):
            return response

        response['Vary'] = 'Accept-Encoding'
        # One shared cache entry must never carry a Set-Cookie, or the first
        # visitor's session would be handed to everyone who hits the same entry.
        # It is also a second reason Cloudflare would refuse to store it.
        if response.has_header('Set-Cookie'):
            del response['Set-Cookie']
        return response


def _client_gone_response(request, context):
    """
    Build the 499 ("Client Closed Request") returned when the peer is already gone.

    Two details keep this quiet in the logs:

    * 499 is an nginx extension with no entry in http.client.responses, so
      HttpResponse.reason_phrase would fall back to the literal string
      "Unknown Status Code". Set the phrase explicitly.
    * BaseHandler.get_response{,_async}() calls log_response() for every
      response with status >= 400, which logs "<reason_phrase>: <path>" at
      WARNING. A client hanging up is not a server error, so mark the response
      as already logged and keep our own DEBUG line instead.
    """
    logger.debug("%s: %s %s", context, request.method, request.path)
    response = JsonResponse({"error": "Connection closed"}, status=499)
    response.reason_phrase = "Client Closed Request"
    response._has_been_logged = True
    return response


class ConnectionAbortMiddleware:
    """
    Turn abrupt client disconnections into a quiet 499 instead of a traceback.

    Two exception types are deliberately NOT caught here:

    * asyncio.CancelledError — ASGIHandler.handle() cancels the request task
      when it sees http.disconnect and expects the task to re-raise, so it can
      skip response.close() and fire request_finished. Swallowing it makes
      Django write a response to a dead socket and lets the view keep spending
      DB/CPU on a client that already left.
    * SystemExit — gunicorn raises this in the worker (sys.exit(1) on SIGABRT)
      when it kills a worker that blew past its timeout. Catching it stops the
      worker from exiting as intended.

    Supports both sync and async (ASGI) request paths.
    """

    sync_capable = True
    async_capable = True

    def __init__(self, get_response):
        self.get_response = get_response
        if iscoroutinefunction(self.get_response):
            markcoroutinefunction(self)

    def __call__(self, request):
        if iscoroutinefunction(self.get_response):
            return self.__acall__(request)
        try:
            return self.get_response(request)
        except (BrokenPipeError, ConnectionResetError):
            return _client_gone_response(request, "Connection closed during request")

    async def __acall__(self, request):
        try:
            return await self.get_response(request)
        except asyncio.CancelledError:
            logger.debug(
                "Request cancelled, client disconnected: %s %s", request.method, request.path
            )
            raise
        except (BrokenPipeError, ConnectionResetError):
            return _client_gone_response(request, "Connection closed during request (ASGI)")
