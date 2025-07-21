from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from superapp.apps.admin_portal.admin import SuperAppModelAdmin
from superapp.apps.admin_portal.sites import superapp_admin_site
from ..models import Artists
from ..services import AutocompleteService


@admin.register(Artists, site=superapp_admin_site)
class ArtistsAdmin(SuperAppModelAdmin):
    list_display = ['name', 'thumbnail_preview', 'created_at', 'updated_at']
    list_filter = ['dirty_metadata', 'created_at', 'updated_at']
    search_fields = ['name']
    readonly_fields = ['thumbnail_url', 'created_at', 'updated_at', 'thumbnail_preview']
    fields = ['dirty_metadata', 'name', 'thumbnail', 'thumbnail_preview', 'thumbnail_url', 'created_at', 'updated_at']

    # Optimization for large datasets
    list_per_page = 25
    list_max_show_all = 100
    show_full_result_count = False

    def thumbnail_preview(self, obj):
        if obj.thumbnail_url:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 4px;" />',
                obj.thumbnail_url
            )
        return _("No image")
    thumbnail_preview.short_description = _("Preview")

    def get_queryset(self, request):
        # Optimize queryset for performance
        return super().get_queryset(request)

    def get_search_results(self, request, queryset, search_term):
        """
        Override search to use fast trigram-based search for better autocomplete performance
        """
        if not search_term or len(search_term.strip()) < 2:
            return queryset, False

        # Use the autocomplete service for fast trigram search
        search_results = AutocompleteService.search_artists(
            search_term.strip(), 
            limit=100  # Higher limit for admin interface
        )
        
        # Convert QuerySet to list of IDs to maintain compatibility with admin interface
        result_ids = [artist.id for artist in search_results]
        
        if result_ids:
            # Preserve ordering from the autocomplete service
            queryset = queryset.filter(id__in=result_ids)
            # Apply manual ordering to match the search result order
            ordering = {id_: index for index, id_ in enumerate(result_ids)}
            queryset = sorted(queryset, key=lambda x: ordering.get(x.id, 999))
            return queryset, False
        else:
            return queryset.none(), False
