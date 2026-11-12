from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from superapp.apps.admin_portal.admin import SuperAppModelAdmin
from superapp.apps.admin_portal.sites import superapp_admin_site
from ..models import AnnouncementCategory


@admin.register(AnnouncementCategory, site=superapp_admin_site)
class AnnouncementCategoryAdmin(SuperAppModelAdmin):
    list_display = ['name', 'slug', 'tag_preview', 'ordering']
    list_editable = ['ordering']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['tag_preview', 'created_at', 'updated_at']
    fields = ['name', 'slug', 'color', 'tag_preview', 'ordering', 'created_at', 'updated_at']

    @admin.display(description=_('Tag'))
    def tag_preview(self, obj):
        if not obj or not obj.color:
            return '-'
        return format_html(
            '<span style="background:{};color:{};border-radius:999px;padding:2px 10px;font-size:12px;'
            'font-weight:600">{}</span>',
            obj.color, obj.text_color, obj.name,
        )
