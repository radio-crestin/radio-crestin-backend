import os
from functools import wraps
from django.http import HttpResponse


def cors_exempt(view_func):
    """
    Decorator to add CORS headers to a view, similar to csrf_exempt.
    Allows cross-origin requests to the decorated view.
    """
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        # Handle preflight OPTIONS request
        if request.method == 'OPTIONS':
            response = HttpResponse()
        else:
            response = view_func(request, *args, **kwargs)

        # Get allowed origins from environment variable
        allowed_origins_env = os.environ.get('GRAPHQL_CORS_ALLOWED_ORIGINS', '').strip()
        allow_all_origins = os.environ.get('GRAPHQL_CORS_ALLOW_ALL_ORIGINS', 'false').lower() == 'true'

        # Get the origin from the request
        origin = request.headers.get('Origin')

        if allow_all_origins and origin:
            # Allow all origins
            response['Access-Control-Allow-Origin'] = origin
        elif allowed_origins_env and origin:
            # Check if origin is in allowed list
            allowed_origins = [o.strip() for o in allowed_origins_env.split(',') if o.strip()]
            if origin in allowed_origins:
                response['Access-Control-Allow-Origin'] = origin
        elif origin:
            # Default allowed origins
            default_allowed = [
                'http://localhost:8080',
                'https://radio-crestin-frontend.bringes.workers.dev',
                'https://admin-staging.radio-crestin.com',
            ]
            if origin in default_allowed:
                response['Access-Control-Allow-Origin'] = origin

        # Add other CORS headers only if origin is allowed
        if 'Access-Control-Allow-Origin' in response:
            response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Accept, Accept-Encoding, Authorization, Content-Type, content-type, DNT, Origin, User-Agent, X-CSRFToken, X-Requested-With, Apollo-Require-Preflight'
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Max-Age'] = '86400'  # 24 hours

        return response

    return wrapped_view
