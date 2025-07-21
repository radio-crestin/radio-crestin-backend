from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from superapp.apps.admin_portal.admin import SuperAppModelAdmin
from superapp.apps.admin_portal.sites import superapp_admin_site
from ..models import Artists


@admin.register(Artists, site=superapp_admin_site)
class ArtistsAdmin(SuperAppModelAdmin):
    list_display = ['name', 'thumbnail_preview', 'created_at', 'updated_at']
    list_filter = ['dirty_metadata', 'created_at', 'updated_at']
    search_fields = ['name']
    readonly_fields = ['thumbnail_url', 'created_at', 'updated_at', 'thumbnail_preview']
    fields = ['dirty_metadata', 'name', 'thumbnail', 'thumbnail_preview', 'thumbnail_url', 'created_at', 'updated_at']

    # Optimization for large datasets
    list_per_page = 25
    list_max_show_all = 100
    show_full_result_count = False

    def thumbnail_preview(self, obj):
        if obj.thumbnail_url:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 4px;" />',
                obj.thumbnail_url
            )
        return _("No image")
    thumbnail_preview.short_description = _("Preview")

    def get_queryset(self, request):
        # Optimize queryset for performance
        return super().get_queryset(request).select_related()
