from django.contrib.admin.views.autocomplete import AutocompleteJsonView
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.shortcuts import redirect
import json
from strawberry.django.context import StrawberryDjangoContext
import logging

from .models import Songs, Artists
from .services import AutocompleteService
from .services.share_link_service import ShareLinkService
from .constants import STATIONS_GRAPHQL_QUERY
from superapp.apps.graphql.schema import schema


class FastSongAutocompleteView(AutocompleteJsonView):
    """Fast autocomplete view for songs using trigram indexes"""

    def get_queryset(self):
        """Use the optimized service for fast search"""
        if not self.term or len(self.term.strip()) < 2:
            return Songs.objects.none()

        # Use the autocomplete service for fast trigram-based search
        return AutocompleteService.search_songs(self.term.strip(), limit=20)

    def get_paginator(self, *args, **kwargs):
        """Override paginator since we handle limiting in the service"""
        from django.core.paginator import Paginator
        return Paginator(list(self.get_queryset()), 20)


class FastArtistAutocompleteView(AutocompleteJsonView):
    """Fast autocomplete view for artists using trigram indexes"""

    def get_queryset(self):
        """Use the optimized service for fast search"""
        if not self.term or len(self.term.strip()) < 2:
            return Artists.objects.none()

        # Use the autocomplete service for fast trigram-based search
        return AutocompleteService.search_artists(self.term.strip(), limit=20)

    def get_paginator(self, *args, **kwargs):
        """Override paginator since we handle limiting in the service"""
        from django.core.paginator import Paginator
        return Paginator(list(self.get_queryset()), 20)


class FastAutocompleteJsonView(AutocompleteJsonView):
    """
    Generic fast autocomplete view that can be configured for any model.
    Uses the service layer for optimized trigram-based searching.
    """
    service_method = None

    def get_queryset(self):
        """Use the configured service method for fast search"""
        if not self.term or len(self.term.strip()) < 2:
            return self.model_admin.model.objects.none()

        if not self.service_method:
            # Fallback to default Django behavior
            qs = self.model_admin.get_queryset(self.request)
            qs = qs.complex_filter(self.source_field.get_limit_choices_to())
            qs, search_use_distinct = self.model_admin.get_search_results(
                self.request, qs, self.term
            )
            if search_use_distinct:
                qs = qs.distinct()
            return qs

        # Use the configured service method
        return self.service_method(self.term.strip(), limit=20)

    def get_paginator(self, *args, **kwargs):
        """Override paginator since we handle limiting in the service"""
        from django.core.paginator import Paginator
        return Paginator(list(self.get_queryset()), 20)


def api_autocomplete(request):
    """
    Simple API endpoint for autocomplete that returns JSON data
    Useful for frontend applications that need autocomplete data
    """
    query = request.GET.get('q', '').strip()
    search_type = request.GET.get('type', 'combined')
    limit = int(request.GET.get('limit', 10))

    if not query or len(query) < 2:
        return JsonResponse({'results': []})

    try:
        suggestions = AutocompleteService.get_autocomplete_suggestions(
            query=query,
            search_type=search_type,
            limit=limit
        )
        return JsonResponse({'results': suggestions})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


def api_v1_stations(request):
    """
    API endpoint that redirects to a timestamped URL and executes GraphQL query with cache headers.
    """
    # Get current timestamp rounded to 10 seconds
    current_timestamp = timezone.now().timestamp()
    rounded_timestamp = int(current_timestamp // 10) * 10

    # Check if we already have the timestamp parameter
    timestamp_param = request.GET.get('timestamp')

    if not timestamp_param:
        # Redirect to the same URL with timestamp parameter
        redirect_url = f"{request.path}?timestamp={rounded_timestamp}"
        return HttpResponseRedirect(redirect_url)

    # Execute GraphQL query
    graphql_query = STATIONS_GRAPHQL_QUERY

    try:
        # Create a response object that will be used for the context
        response = HttpResponse()

        # Create a context for the GraphQL execution
        context = StrawberryDjangoContext(request=request, response=response)

        # Execute the GraphQL query directly using Strawberry schema
        result = schema.execute_sync(
            graphql_query,
            context_value=context
        )

        # Prepare response data
        response_data = {"data": result.data}

        if result.errors:
            response_data["errors"] = [
                {"message": str(error)} for error in result.errors
            ]

        # Create response with cache headers
        json_response = JsonResponse(response_data)
        json_response['Cache-Control'] = 'public, max-age=14400, immutable'

        return json_response

    except Exception as e:
        return JsonResponse({'error': f'Unexpected error: {str(e)}'}, status=500)


class ShareLinkRedirectView(View):
    """Handle share link redirects and track visits"""
    
    def get(self, request, *args, **kwargs):
        """Process share link and redirect to appropriate destination"""
        logger = logging.getLogger(__name__)
        
        # Get share_id from query parameter
        share_id = request.GET.get('s')
        if not share_id:
            # No share link, redirect to main site
            return redirect('https://www.radiocrestin.ro/')
        
        # Get share link from service
        share_link = ShareLinkService.get_share_link_by_id(share_id)
        if not share_link:
            # Invalid share link, redirect to main site
            logger.warning(f"Invalid share link attempted: {share_id}")
            return redirect('https://www.radiocrestin.ro/')
        
        # Get visitor information
        visitor_ip = request.META.get('REMOTE_ADDR')
        visitor_user_agent = request.META.get('HTTP_USER_AGENT', '')
        visitor_referer = request.META.get('HTTP_REFERER', '')
        
        # Get or create session ID for tracking unique visitors
        if not request.session.session_key:
            request.session.create()
        visitor_session_id = request.session.session_key
        
        # Check if visitor is the share link creator (don't count their visits)
        # We can check by comparing session or anonymous_id if available
        is_creator = False
        if hasattr(request, 'user') and request.user.is_authenticated:
            # Check if authenticated user matches share link creator
            if hasattr(request.user, 'anonymous_id'):
                is_creator = request.user.anonymous_id == share_link.user.anonymous_id
        
        # Track visit if not the creator
        if not is_creator:
            ShareLinkService.track_visit(
                share_id=share_id,
                visitor_ip=visitor_ip,
                visitor_user_agent=visitor_user_agent,
                visitor_referer=visitor_referer,
                visitor_session_id=visitor_session_id
            )
        
        # Build redirect URL
        base_url = 'https://www.radiocrestin.ro'
        if share_link.station:
            redirect_url = f"{base_url}/{share_link.station.slug}"
        else:
            redirect_url = base_url
        
        # Log the redirect
        logger.info(f"Share link {share_id} redirecting to {redirect_url}")
        
        return redirect(redirect_url)


def get_share_link_api(request, user_id):
    """API endpoint to get share links for a user"""
    try:
        # Get share link info from service
        result = ShareLinkService.get_share_link_info(user_id)
        
        if 'error' in result:
            return JsonResponse(result, status=404)
        
        # Add CORS headers if needed
        response = JsonResponse(result)
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET'
        response['Cache-Control'] = 'no-cache'
        
        return response
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error in get_share_link_api: {e}")
        return JsonResponse({'error': str(e)}, status=500)
