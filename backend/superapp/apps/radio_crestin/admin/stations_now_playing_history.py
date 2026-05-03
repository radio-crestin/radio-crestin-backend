from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse

from unfold.contrib.filters.admin import RangeDateTimeFilter, AutocompleteSelectFilter

from superapp.apps.admin_portal.admin import SuperAppModelAdmin
from superapp.apps.admin_portal.sites import superapp_admin_site
from ..models import StationsNowPlayingHistory


@admin.register(StationsNowPlayingHistory, site=superapp_admin_site)
class StationsNowPlayingHistoryAdmin(SuperAppModelAdmin):
    list_display = ['pk', 'station_link', 'song_link', 'timestamp', 'listeners']
    list_filter = [
        ('timestamp', RangeDateTimeFilter),
        ('station', AutocompleteSelectFilter),
    ]
    search_fields = ['station__title', 'song__name']
    autocomplete_fields = ['station', 'song']
    readonly_fields = [
        'timestamp', 'station', 'song', 'listeners',
        'start_epoch', 'end_timestamp', 'end_epoch',
        'id3_timestamp', 'scraper_timestamp', 'timestamp_source',
    ]
    list_select_related = ['station', 'song', 'song__artist']
    ordering = ['-timestamp']

    list_per_page = 25
    show_full_result_count = False

    fieldsets = (
        (_("Basic Information"), {
            'fields': ('station', 'song', 'timestamp', 'listeners')
        }),
        (_("Segment & Timestamps"), {
            'fields': ('start_epoch', 'end_timestamp', 'end_epoch'),
            'description': _("Segment numbers are epoch-based (hls_start_number_source=epoch). "
                             "End timestamp is the start of the next now playing entry for this station."),
        }),
        (_("Detection Sources"), {
            'fields': ('id3_timestamp', 'scraper_timestamp', 'timestamp_source'),
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

    def start_epoch(self, obj):
        if obj.timestamp:
            return int(obj.timestamp.timestamp())
        return '-'
    start_epoch.short_description = _("Start Epoch (≈ segment number)")

    def end_timestamp(self, obj):
        next_entry = StationsNowPlayingHistory.objects.filter(
            station=obj.station,
            timestamp__gt=obj.timestamp,
        ).order_by('timestamp').values_list('timestamp', flat=True).first()
        if next_entry:
            return next_entry
        return _("(current / no next entry)")
    end_timestamp.short_description = _("End Timestamp")

    def end_epoch(self, obj):
        next_entry = StationsNowPlayingHistory.objects.filter(
            station=obj.station,
            timestamp__gt=obj.timestamp,
        ).order_by('timestamp').values_list('timestamp', flat=True).first()
        if next_entry:
            return int(next_entry.timestamp())
        return '-'
    end_epoch.short_description = _("End Epoch (≈ segment number)")
