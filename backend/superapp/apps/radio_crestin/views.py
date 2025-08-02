from django.contrib.admin.views.autocomplete import AutocompleteJsonView
from django.http import JsonResponse, HttpResponseRedirect
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
import json
import requests
from os import environ

from .models import Songs, Artists
from .services import AutocompleteService


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
    graphql_query = '''
    query GetStations {
      stations(order_by: {order: asc, title: asc}){
        id
        order
        title
        website
        slug
        email
        stream_url
        proxy_stream_url
        hls_stream_url
        thumbnail_url
        total_listeners
        radio_crestin_listeners
        description
        description_action_title
        description_link
        feature_latest_post
        station_streams {
          type
          stream_url
          order
        }
        posts(limit: 1, order_by: {published: desc}) {
          id
          title
          description
          link
          published
        }
        uptime {
          is_up
          latency_ms
          timestamp
        }
        now_playing {
          id
          timestamp
          song {
            id
            name
            thumbnail_url
            artist {
              id
              name
              thumbnail_url
            }
          }
        }
        reviews {
          id
          stars
          message
        }
      }
      station_groups {
        id
        name
        order
        station_to_station_groups {
          station_id
          order
        }
      }
    }
    '''
    
    try:
        # Make request to GraphQL endpoint
        graphql_url = request.build_absolute_uri(reverse('graphql'))
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Forward auth headers if present
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if auth_header:
            headers['Authorization'] = auth_header
        
        response = requests.post(
            graphql_url,
            json={'query': graphql_query},
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Create response with cache headers
            json_response = JsonResponse(data)
            json_response['Cache-Control'] = 's-maxage=14400, proxy-revalidate, max-age=0'
            
            return json_response
        else:
            return JsonResponse(
                {'error': f'GraphQL request failed with status {response.status_code}'}, 
                status=response.status_code
            )
            
    except requests.RequestException as e:
        return JsonResponse({'error': f'Request failed: {str(e)}'}, status=500)
    except Exception as e:
        return JsonResponse({'error': f'Unexpected error: {str(e)}'}, status=500)