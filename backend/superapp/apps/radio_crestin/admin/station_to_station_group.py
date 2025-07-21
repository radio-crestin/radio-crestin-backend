from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from superapp.apps.admin_portal.admin import SuperAppModelAdmin
from superapp.apps.admin_portal.sites import superapp_admin_site
from ..models import StationToStationGroup


@admin.register(StationToStationGroup, site=superapp_admin_site)
class StationToStationGroupAdmin(SuperAppModelAdmin):
    list_display = ['station', 'group', 'order', 'created_at']
    list_filter = ['group', 'created_at']
    search_fields = ['station__title', 'group__name']
    autocomplete_fields = ['station', 'group']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['group', 'order']
    
    fieldsets = (
        (_("Relationship"), {
            'fields': ('station', 'group', 'order')
        }),
        (_("Timestamps"), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )