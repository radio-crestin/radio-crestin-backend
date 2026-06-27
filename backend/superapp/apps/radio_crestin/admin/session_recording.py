from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from superapp.apps.admin_portal.admin import SuperAppModelAdmin
from superapp.apps.admin_portal.sites import superapp_admin_site
from ..models import SessionRecordingConfig, SessionRecordingOverride


@admin.register(SessionRecordingConfig, site=superapp_admin_site)
class SessionRecordingConfigAdmin(SuperAppModelAdmin):
    list_display = ['__str__', 'enabled', 'rollout_percentage', 'sample_rate', 'modified_at']
    readonly_fields = ['created_at', 'modified_at']

    fieldsets = (
        (_("Rollout"), {
            'fields': ('enabled', 'rollout_percentage', 'sample_rate')
        }),
        (_("Timestamps"), {
            'fields': ('created_at', 'modified_at'),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        # Single-row config — block adding a second one.
        if SessionRecordingConfig.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(SessionRecordingOverride, site=superapp_admin_site)
class SessionRecordingOverrideAdmin(SuperAppModelAdmin):
    list_display = ['device_id', 'enabled', 'note', 'modified_at']
    list_filter = ['enabled']
    search_fields = ['device_id', 'note']
    readonly_fields = ['created_at', 'modified_at']
    ordering = ['-modified_at']
