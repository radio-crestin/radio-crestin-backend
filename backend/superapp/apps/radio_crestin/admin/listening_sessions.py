from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.utils import timezone
from django.shortcuts import redirect
from django.urls import reverse_lazy
import unfold.decorators

from superapp.apps.admin_portal.admin import SuperAppModelAdmin
from superapp.apps.admin_portal.sites import superapp_admin_site
from ..models import ListeningSessions


@admin.register(ListeningSessions, site=superapp_admin_site)
class ListeningSessionsAdmin(SuperAppModelAdmin):
    actions_list = [
        "delete_all_listening_events",
    ]
    
    list_display = ['session_preview', 'user_display', 'station', 'start_time', 'duration_display', 'ip_address', 'status', 'is_active']
    list_filter = ['station', 'start_time', 'end_time', 'is_active']
    search_fields = ['user__email', 'user__anonymous_id', 'station__title', 'anonymous_session_id', 'ip_address']
    autocomplete_fields = ['user', 'station']
    readonly_fields = ['created_at', 'updated_at', 'duration_display', 'session_preview', 'user_agent_display', 'last_activity']
    date_hierarchy = 'start_time'
    ordering = ['-last_activity']
    
    fieldsets = (
        (_("Session Details"), {
            'fields': ('user', 'station', 'start_time', 'end_time', 'last_activity', 'duration_seconds', 'duration_display', 'is_active')
        }),
        (_("Session Information"), {
            'fields': ('anonymous_session_id', 'session_preview', 'ip_address', 'user_agent', 'user_agent_display', 'referer')
        }),
        (_("Analytics"), {
            'fields': ('total_requests', 'bytes_transferred', 'playlist_requests', 'segment_requests'),
            'classes': ('collapse',)
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
        if obj.anonymous_session_id:
            return format_html('<code>{}</code>', obj.anonymous_session_id[:8] + '...' if len(obj.anonymous_session_id) > 8 else obj.anonymous_session_id)
        return _("No session")
    session_preview.short_description = _("Session ID")
    
    def user_display(self, obj):
        if obj.user:
            return obj.user
        return format_html('<span style="color: #666; font-style: italic;">Anonymous</span>')
    user_display.short_description = _("User")
    
    def user_agent_display(self, obj):
        if obj.user_agent:
            return format_html('<div style="max-width: 400px; word-wrap: break-word;">{}</div>', obj.user_agent)
        return _("No user agent")
    user_agent_display.short_description = _("User Agent")
    
    def status(self, obj):
        if not obj.is_active and obj.end_time:
            return format_html('<span style="color: green;">✓</span> {}'.format(_("Completed")))
        elif obj.is_active:
            return format_html('<span style="color: orange;">●</span> {}'.format(_("Active")))
        else:
            return format_html('<span style="color: red;">⚠</span> {}'.format(_("Inactive")))
    status.short_description = _("Status")
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'station')

    @unfold.decorators.action(description=_("Delete all listening events"))
    def delete_all_listening_events(self, request):
        # Delete all listening sessions
        ListeningSessions.objects.all().delete()
        return redirect(
            reverse_lazy("admin:radio_crestin_listeningsessions_changelist")
        )