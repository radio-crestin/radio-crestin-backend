from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse

from superapp.apps.admin_portal.admin import SuperAppModelAdmin
from superapp.apps.admin_portal.sites import superapp_admin_site
from ..models import Songs


@admin.register(Songs, site=superapp_admin_site)
class SongsAdmin(SuperAppModelAdmin):
    list_display = ['name', 'artist_link', 'thumbnail_preview', 'created_at']
    list_filter = ['created_at', 'updated_at', 'artist']
    search_fields = ['name', 'artist__name']
    autocomplete_fields = ['artist']
    readonly_fields = ['thumbnail_url', 'created_at', 'updated_at', 'thumbnail_preview']
    fields = ['name', 'artist', 'thumbnail', 'thumbnail_preview', 'thumbnail_url', 'created_at', 'updated_at']
    
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