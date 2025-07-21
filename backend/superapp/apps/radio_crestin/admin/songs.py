from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Q

from superapp.apps.admin_portal.admin import SuperAppModelAdmin
from superapp.apps.admin_portal.sites import superapp_admin_site
from ..models import Songs
from ..services import AutocompleteService


@admin.register(Songs, site=superapp_admin_site)
class SongsAdmin(SuperAppModelAdmin):
    list_display = ['name', 'artist_link', 'thumbnail_preview', 'created_at']
    list_filter = ['dirty_metadata', 'created_at', 'updated_at', 'artist']
    search_fields = ['name', 'artist__name']
    autocomplete_fields = ['artist']
    readonly_fields = ['thumbnail_url', 'created_at', 'updated_at', 'thumbnail_preview']
    fields = ['dirty_metadata', 'name', 'artist', 'thumbnail', 'thumbnail_preview', 'thumbnail_url', 'created_at', 'updated_at']

    # Optimization for large datasets
    list_per_page = 25
    list_max_show_all = 100
    show_full_result_count = False
    list_select_related = ['artist']

    def artist_link(self, obj):
        if obj.artist:
            url = reverse('admin:radio_crestin_artists_change', args=[obj.artist.pk])
            return format_html('<a href="{}">{}</a>', url, obj.artist.name)
        return _("No artist")
    artist_link.short_description = _("Artist")
    artist_link.admin_order_field = 'artist__name'

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
        return super().get_queryset(request).select_related('artist')

    def get_search_results(self, request, queryset, search_term):
        """
        Override search to use fast trigram-based search for better autocomplete performance
        """
        if not search_term or len(search_term.strip()) < 2:
            return queryset, False

        # Use the autocomplete service for fast trigram search
        search_results = AutocompleteService.search_songs(
            search_term.strip(), 
            limit=100,  # Higher limit for admin interface
            include_artist=True
        )
        
        # Convert QuerySet to list of IDs to maintain compatibility with admin interface
        result_ids = [song.id for song in search_results]
        
        if result_ids:
            # Preserve ordering from the autocomplete service
            queryset = queryset.filter(id__in=result_ids)
            # Apply manual ordering to match the search result order
            ordering = {id_: index for index, id_ in enumerate(result_ids)}
            queryset = sorted(queryset, key=lambda x: ordering.get(x.id, 999))
            return queryset, False
        else:
            return queryset.none(), False
