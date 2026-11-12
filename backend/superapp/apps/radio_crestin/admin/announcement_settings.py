import unfold.decorators
from django.contrib import admin, messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from superapp.apps.admin_portal.admin import SuperAppModelAdmin
from superapp.apps.admin_portal.sites import superapp_admin_site
from ..models import AnnouncementSettings
from ..models.announcement_settings import new_preview_token


@admin.register(AnnouncementSettings, site=superapp_admin_site)
class AnnouncementSettingsAdmin(SuperAppModelAdmin):
    list_display = ['__str__', 'rotation_mode', 'autoplay_seconds', 'max_per_load', 'updated_at']
    fields = ['rotation_mode', 'autoplay_seconds', 'max_per_load', 'preview_links', 'created_at', 'updated_at']
    readonly_fields = ['preview_links', 'created_at', 'updated_at']
    actions_detail = ['rotate_preview_token']

    def has_add_permission(self, request):
        # A single row: block adding a second one.
        return not AnnouncementSettings.objects.exists() and super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description=_('Preview links'))
    def preview_links(self, obj):
        if not obj or not obj.pk:
            return '-'
        return format_html(
            '<div>{}</div><div><a href="{}" target="_blank" rel="noopener">{}</a></div>'
            '<div><code style="user-select:all">{}</code></div>',
            _('Announcements with the Preview status show only through these links:'),
            obj.website_preview_url, obj.website_preview_url, obj.app_preview_url,
        )

    @unfold.decorators.action(description=_('Rotate preview token'), permissions=['change'])
    def rotate_preview_token(self, request, object_id):
        settings = get_object_or_404(AnnouncementSettings, pk=object_id)
        settings.preview_token = new_preview_token()
        settings.save(update_fields=['preview_token', 'updated_at'])
        messages.success(request, _('New preview token: the old preview links stopped working.'))
        return redirect(reverse('admin:radio_crestin_announcementsettings_change', args=(object_id,)))
