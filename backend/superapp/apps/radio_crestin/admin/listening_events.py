from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.utils import timezone

from superapp.apps.admin_portal.admin import SuperAppModelAdmin
from superapp.apps.admin_portal.sites import superapp_admin_site
from ..models import ListeningEvents


@admin.register(ListeningEvents, site=superapp_admin_site)
class ListeningEventsAdmin(SuperAppModelAdmin):
    list_display = ['user', 'station', 'start_time', 'duration_display', 'session_preview', 'ip_address', 'status']
    list_filter = ['station', 'start_time', 'end_time']
    search_fields = ['user__username', 'user__email', 'station__title', 'session_id', 'ip_address']
    autocomplete_fields = ['user', 'station']
    readonly_fields = ['created_at', 'updated_at', 'duration_display', 'session_preview', 'user_agent_display']
    date_hierarchy = 'start_time'
    ordering = ['-start_time']
    
    fieldsets = (
        (_("Event Details"), {
            'fields': ('user', 'station', 'start_time', 'end_time', 'duration_seconds', 'duration_display')
        }),
        (_("Session Information"), {
            'fields': ('session_id', 'session_preview', 'ip_address', 'user_agent', 'user_agent_display')
        }),
        (_("Additional Data"), {
            'fields': ('info',),
            'classes': ('collapse',)
        }),
        (_("Timestamps"), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def duration_display(self, obj):
        if obj.duration_seconds:
            hours = obj.duration_seconds // 3600
            minutes = (obj.duration_seconds % 3600) // 60
            seconds = obj.duration_seconds % 60
            
            if hours > 0:
                return f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"
        return _("0s")
    duration_display.short_description = _("Duration")
    
    def session_preview(self, obj):
        if obj.session_id:
            return format_html('<code>{}</code>', obj.session_id[:8] + '...' if len(obj.session_id) > 8 else obj.session_id)
        return _("No session")
    session_preview.short_description = _("Session")
    
    def user_agent_display(self, obj):
        if obj.user_agent:
            return format_html('<div style="max-width: 400px; word-wrap: break-word;">{}</div>', obj.user_agent)
        return _("No user agent")
    user_agent_display.short_description = _("User Agent")
    
    def status(self, obj):
        if obj.end_time:
            return format_html('<span style="color: green;">✓</span> {}'.format(_("Completed")))
        else:
            return format_html('<span style="color: orange;">●</span> {}'.format(_("In Progress")))
    status.short_description = _("Status")
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'station')