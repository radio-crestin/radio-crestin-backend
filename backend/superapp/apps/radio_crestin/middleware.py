"""
Subdomain routing middleware for asculta.radiocrestin.ro
"""
from . import views


class SubdomainRoutingMiddleware:
    """
    Middleware to route asculta subdomain requests to ShareLinkRedirectView.
    Handles asculta.radiocrestin.ro/* and asculta.localhost/*
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.view = views.ShareLinkRedirectView.as_view()
    
    def __call__(self, request):
        # Get the host without port
        host = request.get_host().lower().split(':')[0]
        
        # Check if this is the asculta subdomain
        if host.startswith('asculta.'):
            # Get the path (remove leading slash)
            station_path = request.path_info.lstrip('/')
            
            # Call ShareLinkRedirectView with station_path as kwarg
            return self.view(request, station_path=station_path)
        
        # Process normally for non-asculta subdomains
        return self.get_response(request)