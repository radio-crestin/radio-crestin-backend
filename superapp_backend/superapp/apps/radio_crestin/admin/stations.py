from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from superapp.apps.admin_portal.admin import SuperAppModelAdmin, SuperAppTabularInline
from superapp.apps.admin_portal.sites import superapp_admin_site
from ..models import Stations, StationToStationGroup, StationStreams, StationsMetadataFetch


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


@admin.register(Stations, site=superapp_admin_site)
class StationsAdmin(SuperAppModelAdmin):
    list_display = ['title', 'status_indicator', 'thumbnail_preview', 'order', 'website_link', 'groups_display', 'latest_uptime_status']
    list_filter = ['disabled', 'generate_hls_stream', 'feature_latest_post', 'groups', 'created_at']
    search_fields = ['title', 'slug', 'website', 'email']
    prepopulated_fields = {'slug': ('title',)}
    autocomplete_fields = ['latest_station_uptime', 'latest_station_now_playing']
    readonly_fields = ['thumbnail_url', 'created_at', 'updated_at', 'thumbnail_preview']
    
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