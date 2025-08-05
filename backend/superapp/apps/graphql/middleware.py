import os
import logging

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


class ConnectionAbortMiddleware:
    """
    Middleware to handle client disconnections and other connection issues
    
    This middleware catches SystemExit and other connection-related errors
    that occur when clients disconnect before the request is fully processed.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except SystemExit:
            # Client disconnected - log at debug level only
            logger.debug(f"Client disconnected during request: {request.method} {request.path}")
            # Return a minimal response (client won't receive it but it prevents error propagation)
            return JsonResponse({"error": "Connection closed"}, status=499)  # 499 = Client Closed Request
        except BrokenPipeError:
            # Client closed connection while we were sending response
            logger.debug(f"Broken pipe during response: {request.method} {request.path}")
            return JsonResponse({"error": "Connection closed"}, status=499)
        except ConnectionResetError:
            # Connection reset by peer
            logger.debug(f"Connection reset: {request.method} {request.path}")
            return JsonResponse({"error": "Connection reset"}, status=499)
        except Exception as e:
            # Log other unexpected errors
            logger.error(f"Unexpected error in ConnectionAbortMiddleware: {e}", exc_info=True)
            raise
