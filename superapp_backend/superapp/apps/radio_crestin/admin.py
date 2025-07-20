from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.db import models
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from superapp.apps.admin_portal.admin import SuperAppModelAdmin, SuperAppTabularInline
from superapp.apps.admin_portal.sites import superapp_admin_site
from .models import (
    Artists, Songs, StationGroups, StationMetadataFetchCategories,
    StationToStationGroup, Stations, StationStreams, StationsMetadataFetch,
    Posts, StationsNowPlaying, StationsUptime
)


class StationToStationGroupInline(SuperAppTabularInline):
    model = StationToStationGroup
    fk_name = 'station'
    extra = 0
    autocomplete_fields = ['group']
    fields = ['group', 'order']


class StationStreamsInline(SuperAppTabularInline):
    model = StationStreams
    fk_name = 'station'
    extra = 0
    fields = ['stream_url', 'type', 'order']


class StationsMetadataFetchInline(SuperAppTabularInline):
    model = StationsMetadataFetch
    fk_name = 'station'
    extra = 0
    autocomplete_fields = ['station_metadata_fetch_category']
    fields = ['station_metadata_fetch_category', 'url', 'order']


@admin.register(Artists, site=superapp_admin_site)
class ArtistsAdmin(SuperAppModelAdmin):
    list_display = ['name', 'thumbnail_preview', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['name']
    readonly_fields = ['thumbnail_url', 'created_at', 'updated_at', 'thumbnail_preview']
    fields = ['name', 'thumbnail', 'thumbnail_preview', 'thumbnail_url', 'created_at', 'updated_at']
    
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
        return super().get_queryset(request).select_related()


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


@admin.register(StationGroups, site=superapp_admin_site)
class StationGroupsAdmin(SuperAppModelAdmin):
    list_display = ['name', 'slug', 'order', 'station_count', 'created_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at', 'station_count']
    fields = ['name', 'slug', 'order', 'station_count', 'created_at', 'updated_at']
    
    def station_count(self, obj):
        count = obj.stations.count()
        if count > 0:
            url = reverse('admin:radio_crestin_stations_changelist') + f'?groups__id__exact={obj.pk}'
            return format_html('<a href="{}">{} stations</a>', url, count)
        return _("No stations")
    station_count.short_description = _("Stations")

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('stations')


@admin.register(StationMetadataFetchCategories, site=superapp_admin_site)
class StationMetadataFetchCategoriesAdmin(SuperAppModelAdmin):
    list_display = ['slug', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['slug']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Stations, site=superapp_admin_site)
class StationsAdmin(SuperAppModelAdmin):
    list_display = ['title', 'status_indicator', 'thumbnail_preview', 'order', 'website_link', 'groups_display', 'latest_uptime_status']
    list_filter = ['disabled', 'generate_hls_stream', 'feature_latest_post', 'groups', 'created_at']
    search_fields = ['title', 'slug', 'website', 'email']
    prepopulated_fields = {'slug': ('title',)}
    autocomplete_fields = ['latest_station_uptime', 'latest_station_now_playing']
    readonly_fields = ['thumbnail_url', 'created_at', 'updated_at', 'thumbnail_preview']
    filter_horizontal = ['groups']
    
    fieldsets = (
        (_("Basic Information"), {
            'fields': ('title', 'slug', 'order', 'disabled', 'website', 'email')
        }),
        (_("Streaming"), {
            'fields': ('stream_url', 'generate_hls_stream')
        }),
        (_("Media"), {
            'fields': ('thumbnail', 'thumbnail_preview', 'thumbnail_url')
        }),
        (_("Content"), {
            'fields': ('description', 'description_action_title', 'description_link')
        }),
        (_("RSS & Social"), {
            'fields': ('rss_feed', 'feature_latest_post', 'facebook_page_id')
        }),
        (_("Status"), {
            'fields': ('latest_station_uptime', 'latest_station_now_playing')
        }),
        (_("Timestamps"), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [StationToStationGroupInline, StationStreamsInline, StationsMetadataFetchInline]
    
    def status_indicator(self, obj):
        if obj.disabled:
            return format_html('<span style="color: red;">●</span> {}'.format(_("Disabled")))
        return format_html('<span style="color: green;">●</span> {}'.format(_("Active")))
    status_indicator.short_description = _("Status")
    status_indicator.admin_order_field = 'disabled'

    def thumbnail_preview(self, obj):
        if obj.thumbnail_url:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 4px;" />',
                obj.thumbnail_url
            )
        return _("No image")
    thumbnail_preview.short_description = _("Preview")

    def website_link(self, obj):
        if obj.website:
            return format_html('<a href="{}" target="_blank">{}</a>', obj.website, obj.website[:30] + "..." if len(obj.website) > 30 else obj.website)
        return _("No website")
    website_link.short_description = _("Website")

    def groups_display(self, obj):
        groups = obj.groups.all()[:3]  # Limit to first 3 groups
        if groups:
            group_links = []
            for group in groups:
                url = reverse('admin:radio_crestin_stationgroups_change', args=[group.pk])
                group_links.append(format_html('<a href="{}">{}</a>', url, group.name))
            result = ', '.join(group_links)
            if obj.groups.count() > 3:
                result += f' +{obj.groups.count() - 3} more'
            return mark_safe(result)
        return _("No groups")
    groups_display.short_description = _("Groups")

    def latest_uptime_status(self, obj):
        if obj.latest_station_uptime:
            uptime = obj.latest_station_uptime
            status = _("Up") if uptime.is_up else _("Down")
            color = "green" if uptime.is_up else "red"
            return format_html(
                '<span style="color: {};">{}</span> ({}ms)',
                color, status, uptime.latency_ms
            )
        return _("No data")
    latest_uptime_status.short_description = _("Latest Status")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'latest_station_uptime', 
            'latest_station_now_playing'
        ).prefetch_related('groups')


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


@admin.register(Posts, site=superapp_admin_site)
class PostsAdmin(SuperAppModelAdmin):
    list_display = ['title_short', 'station_link', 'published', 'created_at']
    list_filter = ['published', 'created_at', 'station']
    search_fields = ['title', 'description', 'station__title']
    autocomplete_fields = ['station']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'published'
    list_select_related = ['station']
    
    # Optimization for large datasets
    list_per_page = 25
    show_full_result_count = False
    
    def title_short(self, obj):
        return obj.title[:50] + "..." if len(obj.title) > 50 else obj.title
    title_short.short_description = _("Title")
    title_short.admin_order_field = 'title'

    def station_link(self, obj):
        if obj.station:
            url = reverse('admin:radio_crestin_stations_change', args=[obj.station.pk])
            return format_html('<a href="{}">{}</a>', url, obj.station.title)
        return _("No station")
    station_link.short_description = _("Station")
    station_link.admin_order_field = 'station__title'


@admin.register(StationsNowPlaying, site=superapp_admin_site)
class StationsNowPlayingAdmin(SuperAppModelAdmin):
    list_display = ['station_link', 'song_link', 'timestamp', 'listeners', 'has_error']
    list_filter = ['timestamp', 'station', 'song__artist']
    search_fields = ['station__title', 'song__name', 'song__artist__name']
    autocomplete_fields = ['station', 'song']
    readonly_fields = ['created_at', 'updated_at', 'raw_data_preview', 'error_preview']
    date_hierarchy = 'timestamp'
    list_select_related = ['station', 'song', 'song__artist']
    
    # Optimization for large datasets
    list_per_page = 25
    show_full_result_count = False
    
    fieldsets = (
        (_("Basic Information"), {
            'fields': ('station', 'song', 'timestamp', 'listeners')
        }),
        (_("Data"), {
            'fields': ('raw_data_preview', 'error_preview'),
            'classes': ('collapse',)
        }),
        (_("Timestamps"), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
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
            return format_html('<a href="{}">{} - {}</a>', url, obj.song.name, obj.song.artist.name)
        return _("No song")
    song_link.short_description = _("Song")
    song_link.admin_order_field = 'song__name'

    def has_error(self, obj):
        if obj.error:
            return format_html('<span style="color: red;">●</span> {}'.format(_("Error")))
        return format_html('<span style="color: green;">●</span> {}'.format(_("OK")))
    has_error.short_description = _("Status")

    def raw_data_preview(self, obj):
        if obj.raw_data:
            import json
            return format_html('<pre>{}</pre>', json.dumps(obj.raw_data, indent=2)[:500] + "...")
        return _("No data")
    raw_data_preview.short_description = _("Raw Data Preview")

    def error_preview(self, obj):
        if obj.error:
            import json
            return format_html('<pre style="color: red;">{}</pre>', json.dumps(obj.error, indent=2)[:500] + "...")
        return _("No errors")
    error_preview.short_description = _("Error Preview")


@admin.register(StationsUptime, site=superapp_admin_site)
class StationsUptimeAdmin(SuperAppModelAdmin):
    list_display = ['station_link', 'status_indicator', 'latency_ms', 'timestamp']
    list_filter = ['is_up', 'timestamp', 'station']
    search_fields = ['station__title']
    autocomplete_fields = ['station']
    readonly_fields = ['created_at', 'updated_at', 'raw_data_preview']
    date_hierarchy = 'timestamp'
    list_select_related = ['station']
    
    # Optimization for large datasets
    list_per_page = 25
    show_full_result_count = False
    
    fieldsets = (
        (_("Basic Information"), {
            'fields': ('station', 'timestamp', 'is_up', 'latency_ms')
        }),
        (_("Data"), {
            'fields': ('raw_data_preview',),
            'classes': ('collapse',)
        }),
        (_("Timestamps"), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def station_link(self, obj):
        if obj.station:
            url = reverse('admin:radio_crestin_stations_change', args=[obj.station.pk])
            return format_html('<a href="{}">{}</a>', url, obj.station.title)
        return _("No station")
    station_link.short_description = _("Station")
    station_link.admin_order_field = 'station__title'

    def status_indicator(self, obj):
        if obj.is_up:
            return format_html('<span style="color: green;">●</span> {}'.format(_("Up")))
        return format_html('<span style="color: red;">●</span> {}'.format(_("Down")))
    status_indicator.short_description = _("Status")
    status_indicator.admin_order_field = 'is_up'

    def raw_data_preview(self, obj):
        if obj.raw_data:
            import json
            return format_html('<pre>{}</pre>', json.dumps(obj.raw_data, indent=2)[:500] + "...")
        return _("No data")
    raw_data_preview.short_description = _("Raw Data Preview")