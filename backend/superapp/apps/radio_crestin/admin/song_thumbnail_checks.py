from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from superapp.apps.admin_portal.admin import SuperAppModelAdmin
from superapp.apps.admin_portal.sites import superapp_admin_site
from ..models import SongThumbnailChecks


@admin.register(SongThumbnailChecks, site=superapp_admin_site)
class SongThumbnailChecksAdmin(SuperAppModelAdmin):
    """Read-only: rows are written by the check_song_thumbnail task.
    Deleting a row makes the URL be checked again."""

    list_display = ['url', 'thumbnail_preview', 'is_placeholder', 'created_at']
    list_filter = ['is_placeholder', 'created_at']
    search_fields = ['url', 'sha256']
    readonly_fields = ['url', 'thumbnail_preview', 'is_placeholder', 'sha256',
                       'created_at', 'updated_at']
    fields = readonly_fields
    list_per_page = 50
    show_full_result_count = False

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def thumbnail_preview(self, obj):
        return format_html(
            '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 4px;" />',
            obj.url
        )
    thumbnail_preview.short_description = _("Preview")
