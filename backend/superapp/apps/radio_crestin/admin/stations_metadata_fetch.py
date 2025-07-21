from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from superapp.apps.admin_portal.admin import SuperAppModelAdmin
from superapp.apps.admin_portal.sites import superapp_admin_site
from ..models import StationsMetadataFetch


@admin.register(StationsMetadataFetch, site=superapp_admin_site)
class StationsMetadataFetchAdmin(SuperAppModelAdmin):
    list_display = ['station', 'station_metadata_fetch_category', 'url_preview', 'priority', 'created_at']
    list_filter = ['station_metadata_fetch_category', 'created_at']
    search_fields = ['station__title', 'url', 'station_metadata_fetch_category__name']
    autocomplete_fields = ['station', 'station_metadata_fetch_category']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['station', '-priority']
    
    fieldsets = (
        (_("Basic Configuration"), {
            'fields': ('station', 'station_metadata_fetch_category', 'url', 'priority', 'dirty_metadata')
        }),
        (_("Regex Configuration"), {
            'fields': ('split_character', 'station_name_regex', 'artist_regex', 'title_regex'),
            'classes': ('collapse',)
        }),
        (_("Timestamps"), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def url_preview(self, obj):
        if obj.url:
            truncated = obj.url[:50] + '...' if len(obj.url) > 50 else obj.url
            return format_html('<code>{}</code>', truncated)
        return _("No URL")
    url_preview.short_description = _("URL")