import json
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse

from superapp.apps.admin_portal.admin import SuperAppModelAdmin
from superapp.apps.admin_portal.sites import superapp_admin_site
from ..models import StationsUptime


@admin.register(StationsUptime, site=superapp_admin_site)
class StationsUptimeAdmin(SuperAppModelAdmin):
    list_display = ['station_link', 'status_indicator', 'latency_ms', 'timestamp']
    list_filter = ['is_up', 'timestamp', 'station']
    search_fields = ['station__title']
    autocomplete_fields = ['station']
    readonly_fields = ['created_at', 'updated_at', 'raw_data']
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
            'fields': ('raw_data',),
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
