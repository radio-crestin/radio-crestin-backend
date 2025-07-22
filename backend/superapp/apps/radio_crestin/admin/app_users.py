from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.contrib import messages
from django.db.models import Q

from superapp.apps.admin_portal.admin import SuperAppModelAdmin
from superapp.apps.admin_portal.sites import superapp_admin_site
from ..models import AppUsers


@admin.register(AppUsers, site=superapp_admin_site)
class AppUsersAdmin(SuperAppModelAdmin):
    list_display = ['id', 'email', 'anonymous_id', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['email', 'anonymous_id']
    readonly_fields = ['created_at', 'modified_at', 'date_joined']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        (_("User Info"), {
            'fields': ('email', 'first_name', 'last_name', 'anonymous_id')
        }),
        (_("Status"), {
            'fields': ('is_active', 'is_staff', 'is_superuser')
        }),
        (_("Timestamps"), {
            'fields': ('created_at', 'modified_at', 'date_joined', 'last_login'),
            'classes': ('collapse',)
        }),
    )
    
    def has_delete_permission(self, request, obj=None):
        # Prevent accidental deletion of users
        return False