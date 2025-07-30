import os

from django.contrib.auth import get_user_model
from django.http import JsonResponse


class GraphQlSuperuserApiAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.api_key = os.getenv('ADMIN_GRAPHQL_SUPERUSER_API_KEY')

    def __call__(self, request):
        # The authentication is disabled for now
        if request.path == '/graphql' or request.path == '/v1/graphql' or request.path == '/v2/graphql':
            auth_header = request.headers.get('Authorization')
            if not request.user.is_authenticated:
                if auth_header and self.api_key and auth_header.endswith(self.api_key):
                    # Authenticate user as first superuser
                    request.user = get_user_model().objects.filter(is_superuser=True).first()

        response = self.get_response(request)
        return response
