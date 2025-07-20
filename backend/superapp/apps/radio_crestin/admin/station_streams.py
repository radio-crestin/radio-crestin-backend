from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse

from superapp.apps.admin_portal.admin import SuperAppModelAdmin
from superapp.apps.admin_portal.sites import superapp_admin_site
from ..models import StationStreams


@admin.register(StationStreams, site=superapp_admin_site)
class StationStreamsAdmin(SuperAppModelAdmin):
    list_display = ['station_link', 'stream_url_short', 'type', 'order', 'created_at']
    list_filter = ['type', 'created_at', 'station']
    search_fields = ['stream_url', 'station__title']
    autocomplete_fields = ['station']
    readonly_fields = ['created_at', 'updated_at']
    list_select_related = ['station']
    
    def station_link(self, obj):
        if obj.station:
            url = reverse('admin:radio_crestin_stations_change', args=[obj.station.pk])
            return format_html('<a href="{}">{}</a>', url, obj.station.title)
        return _("No station")
    station_link.short_description = _("Station")
    station_link.admin_order_field = 'station__title'

    def stream_url_short(self, obj):
        return obj.stream_url[:50] + "..." if len(obj.stream_url) > 50 else obj.stream_url
    stream_url_short.short_description = _("Stream URL")