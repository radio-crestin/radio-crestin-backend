from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse

from superapp.apps.admin_portal.admin import SuperAppModelAdmin
from superapp.apps.admin_portal.sites import superapp_admin_site
from ..models import StationPlaylistItems


@admin.register(StationPlaylistItems, site=superapp_admin_site)
class StationPlaylistItemsAdmin(SuperAppModelAdmin):
    list_display = ['station_link', 'type', 'title_short', 'url_short', 'playlist_item_order', 'enabled', 'created_at']
    list_filter = ['type', 'enabled', 'created_at', 'station']
    search_fields = ['title', 'url', 'station__title']
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

    def title_short(self, obj):
        if not obj.title:
            return _("(untitled)")
        return obj.title[:50] + "..." if len(obj.title) > 50 else obj.title
    title_short.short_description = _("Title")

    def url_short(self, obj):
        return obj.url[:50] + "..." if len(obj.url) > 50 else obj.url
    url_short.short_description = _("URL")
