from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse

from superapp.apps.admin_portal.admin import SuperAppModelAdmin
from superapp.apps.admin_portal.sites import superapp_admin_site
from ..models import StationGroups


@admin.register(StationGroups, site=superapp_admin_site)
class StationGroupsAdmin(SuperAppModelAdmin):
    list_display = ['name', 'slug', 'station_group_order', 'station_count', 'created_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at', 'station_count', 'order']
    fields = ['name', 'slug', 'station_group_order', 'station_count', 'created_at', 'updated_at']

    def station_count(self, obj):
        count = obj.stations.count()
        if count > 0:
            url = reverse('admin:radio_crestin_stations_changelist') + f'?groups__id__exact={obj.pk}'
            return format_html('<a href="{}">{} stations</a>', url, count)
        return _("No stations")
    station_count.short_description = _("Stations")

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('stations')
