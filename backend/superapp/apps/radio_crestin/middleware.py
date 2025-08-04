"""
Simplified subdomain routing middleware for asculta.radiocrestin.ro
"""
from django.shortcuts import redirect
from django.http import HttpResponse
from .services.share_link_service import ShareLinkService
import logging

logger = logging.getLogger(__name__)


class SubdomainRoutingMiddleware:
    """
    Simple middleware to handle asculta subdomain redirects with share link tracking.
    Routes asculta.radiocrestin.ro/* and asculta.localhost/* to radiocrestin.ro/*
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Get the host without port
        host = request.get_host().lower().split(':')[0]
        
        # Check if this is the asculta subdomain
        if host.startswith('asculta.'):
            # Get the path (remove leading slash)
            path = request.path_info.lstrip('/')
            
            # Build redirect URL
            base_url = 'https://www.radiocrestin.ro'
            if path:
                redirect_url = f"{base_url}/{path}"
            else:
                redirect_url = base_url
            
            # Handle share link tracking if 's' parameter exists
            share_id = request.GET.get('s')
            if share_id:
                # Track the visit
                try:
                    # Get visitor information
                    visitor_ip = request.META.get('REMOTE_ADDR', '')
                    visitor_user_agent = request.META.get('HTTP_USER_AGENT', '')
                    visitor_referer = request.META.get('HTTP_REFERER', '')
                    
                    # Create session if needed for unique visitor tracking
                    if hasattr(request, 'session'):
                        if not request.session.session_key:
                            request.session.create()
                        visitor_session_id = request.session.session_key
                    else:
                        visitor_session_id = ''
                    
                    # Track the visit
                    ShareLinkService.track_visit(
                        share_id=share_id,
                        visitor_ip=visitor_ip,
                        visitor_user_agent=visitor_user_agent,
                        visitor_referer=visitor_referer,
                        visitor_session_id=visitor_session_id
                    )
                    
                    # Add ref parameter to redirect URL
                    ref = request.GET.get('ref', 'share')
                    separator = '&' if '?' in redirect_url else '?'
                    redirect_url = f"{redirect_url}{separator}ref={ref}"
                    
                except Exception as e:
                    logger.error(f"Error tracking share link visit: {e}")
            
            # Return redirect response
            return redirect(redirect_url)
        
        # Process normally for non-asculta subdomains
        return self.get_response(request)