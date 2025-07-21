from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from superapp.apps.admin_portal.admin import SuperAppModelAdmin
from superapp.apps.admin_portal.sites import superapp_admin_site
from ..models import StationScrapingTaskState


@admin.register(StationScrapingTaskState, site=superapp_admin_site)
class StationScrapingTaskStateAdmin(SuperAppModelAdmin):
    list_display = ['station', 'current_task_id', 'current_task_started_at', 'last_successful_update_at', 'created_at']
    list_filter = ['created_at', 'updated_at', 'current_task_started_at', 'last_successful_update_at']
    search_fields = ['station__title', 'station__slug', 'current_task_id', 'last_successful_task_id']
    readonly_fields = ['created_at', 'updated_at', 'processed_fetcher_states']
    autocomplete_fields = ['station']
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('station',)
        }),
        (_('Current Task'), {
            'fields': ('current_task_id', 'current_task_started_at'),
            'classes': ['collapse']
        }),
        (_('Task History'), {
            'fields': ('last_successful_update_at', 'last_successful_task_id'),
            'classes': ['collapse']
        }),
        (_('Fetcher States'), {
            'fields': ('processed_fetcher_states',),
            'classes': ['collapse']
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ['collapse']
        }),
    )