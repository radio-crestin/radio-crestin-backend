from django.contrib import admin

from superapp.apps.admin_portal.admin import SuperAppModelAdmin
from superapp.apps.admin_portal.sites import superapp_admin_site
from ..models import AnnouncementSettings


@admin.register(AnnouncementSettings, site=superapp_admin_site)
class AnnouncementSettingsAdmin(SuperAppModelAdmin):
    list_display = ['__str__', 'rotation_mode', 'autoplay_seconds', 'max_per_load', 'updated_at']
    fields = ['rotation_mode', 'autoplay_seconds', 'max_per_load', 'created_at', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']

    def has_add_permission(self, request):
        # A single row: block adding a second one.
        return not AnnouncementSettings.objects.exists() and super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False
