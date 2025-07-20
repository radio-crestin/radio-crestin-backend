from django.contrib.auth import authenticate


class TokenAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get the token from the request header
        token = request.headers.get('Authorization', "")
        if not token.startswith("Token "):
            return self.get_response(request)

        # Perform authentication
        user = authenticate(request=request, token=token)

        if user is not None:
            # Authentication successful, set the authenticated user in the request
            request.user = user

        response = self.get_response(request)
        return response

