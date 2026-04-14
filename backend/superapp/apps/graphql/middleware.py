import asyncio
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
    Middleware to handle client disconnections and other connection issues.

    Catches CancelledError (ASGI request timeout), SystemExit, BrokenPipe,
    and ConnectionReset to prevent unhandled exceptions from crashing workers.
    Supports both sync and async (ASGI) request paths.
    """

    sync_capable = True
    async_capable = True

    def __init__(self, get_response):
        self.get_response = get_response
        if asyncio.iscoroutinefunction(self.get_response):
            self._is_coroutine = asyncio.coroutines._is_coroutine

    def __call__(self, request):
        if asyncio.iscoroutinefunction(self.get_response):
            return self.__acall__(request)
        try:
            response = self.get_response(request)
            return response
        except (SystemExit, asyncio.CancelledError):
            logger.debug(f"Client disconnected during request: {request.method} {request.path}")
            return JsonResponse({"error": "Connection closed"}, status=499)
        except (BrokenPipeError, ConnectionResetError):
            logger.debug(f"Connection closed during request: {request.method} {request.path}")
            return JsonResponse({"error": "Connection closed"}, status=499)
        except Exception as e:
            logger.error(f"Unexpected error in ConnectionAbortMiddleware: {e}", exc_info=True)
            raise

    async def __acall__(self, request):
        try:
            response = await self.get_response(request)
            return response
        except (asyncio.CancelledError, SystemExit):
            logger.debug(f"Request cancelled (ASGI): {request.method} {request.path}")
            return JsonResponse({"error": "Connection closed"}, status=499)
        except (BrokenPipeError, ConnectionResetError):
            logger.debug(f"Connection closed (ASGI): {request.method} {request.path}")
            return JsonResponse({"error": "Connection closed"}, status=499)
        except Exception as e:
            logger.error(f"Unexpected error in ConnectionAbortMiddleware (async): {e}", exc_info=True)
            raise
