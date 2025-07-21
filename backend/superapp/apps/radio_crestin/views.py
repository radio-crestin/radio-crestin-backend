from django.contrib.admin.views.autocomplete import AutocompleteJsonView
from django.http import JsonResponse
from django.db.models import Q

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