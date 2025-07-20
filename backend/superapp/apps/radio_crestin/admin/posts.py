from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse

from superapp.apps.admin_portal.admin import SuperAppModelAdmin
from superapp.apps.admin_portal.sites import superapp_admin_site
from ..models import Posts


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