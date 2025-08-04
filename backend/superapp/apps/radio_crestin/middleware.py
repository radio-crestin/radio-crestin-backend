"""
Custom subdomain routing middleware for radio_crestin app.
Handles routing for asculta.radiocrestin.ro and asculta.localhost subdomains.
"""
from django.conf import settings
from django.http import HttpResponseNotFound
from django.urls import include, path
from django.core.handlers.wsgi import WSGIHandler
from django.urls import resolve, Resolver404
from . import views


class SubdomainRoutingMiddleware:
    """
    Middleware to handle subdomain-specific routing for the 'asculta' subdomain.
    This allows ShareLinkRedirectView to only be accessible via:
    - asculta.radiocrestin.ro
    - asculta.localhost (for development)
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Define subdomain-specific URL patterns
        self.asculta_patterns = [
            path('', views.ShareLinkRedirectView.as_view(), name='share_link_redirect'),
            path('<path:station_path>', views.ShareLinkRedirectView.as_view(), name='share_link_redirect_with_station'),
        ]
    
    def __call__(self, request):
        # Get the host from the request
        host = request.get_host().lower()
        
        # Remove port if present (for localhost:8080)
        if ':' in host:
            host = host.split(':')[0]
        
        # Check if this is the 'asculta' subdomain
        if host.startswith('asculta.'):
            # Extract the subdomain
            subdomain = host.split('.')[0]
            
            if subdomain == 'asculta':
                # Store original urlconf
                original_urlconf = getattr(request, 'urlconf', None)
                
                # Try to match the path against our subdomain patterns
                try:
                    # Check if the path matches any of our asculta patterns
                    for pattern in self.asculta_patterns:
                        try:
                            # Keep the path as-is, don't strip the leading slash
                            path_to_resolve = request.path_info[1:] if request.path_info.startswith('/') else request.path_info
                            match = pattern.resolve(path_to_resolve)
                            if match:
                                # Call the matched view
                                return match.func(request, *match.args, **match.kwargs)
                        except Resolver404:
                            continue
                    
                    # If no pattern matched, return 404
                    return HttpResponseNotFound("Page not found on asculta subdomain")
                    
                except Exception as e:
                    # Log the error and continue with normal processing
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error in subdomain routing: {e}")
                finally:
                    # Restore original urlconf if it was changed
                    if original_urlconf:
                        request.urlconf = original_urlconf
        
        # Process normally for non-subdomain requests
        response = self.get_response(request)
        return response