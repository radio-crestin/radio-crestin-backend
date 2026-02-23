from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse

from superapp.apps.admin_portal.admin import SuperAppModelAdmin
from superapp.apps.admin_portal.sites import superapp_admin_site
from ..models import StationsNowPlayingHistory


@admin.register(StationsNowPlayingHistory, site=superapp_admin_site)
class StationsNowPlayingHistoryAdmin(SuperAppModelAdmin):
    list_display = ['pk', 'station_link', 'song_link', 'timestamp', 'listeners']
    list_filter = ['timestamp', 'station']
    search_fields = ['station__title', 'song__name', 'song__artist__name']
    autocomplete_fields = ['station', 'song']
    readonly_fields = ['timestamp', 'station', 'song', 'listeners']
    date_hierarchy = 'timestamp'
    list_select_related = ['station', 'song', 'song__artist']

    list_per_page = 25
    show_full_result_count = False

    fieldsets = (
        (_("Basic Information"), {
            'fields': ('station', 'song', 'timestamp', 'listeners')
        }),
    )

    def station_link(self, obj):
        if obj.station:
            url = reverse('admin:radio_crestin_stations_change', args=[obj.station.pk])
            return format_html('<a href="{}">{}</a>', url, obj.station.title)
        return _("No station")
    station_link.short_description = _("Station")
    station_link.admin_order_field = 'station__title'

    def song_link(self, obj):
        if obj.song:
            url = reverse('admin:radio_crestin_songs_change', args=[obj.song.pk])
            artist_name = obj.song.artist.name if obj.song.artist else _("Unknown Artist")
            return format_html('<a href="{}">{} - {}</a>', url, obj.song.name, artist_name)
        return _("No song")
    song_link.short_description = _("Song")
    song_link.admin_order_field = 'song__name'
