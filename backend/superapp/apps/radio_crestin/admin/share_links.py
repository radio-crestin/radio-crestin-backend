from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone

from superapp.apps.admin_portal.admin import SuperAppModelAdmin
from superapp.apps.admin_portal.sites import superapp_admin_site

from ..models import ShareLink, ShareLinkVisit


@admin.register(ShareLink, site=superapp_admin_site)
class ShareLinkAdmin(SuperAppModelAdmin):
    """Admin configuration for ShareLink model"""
    
    list_display = [
        'share_id',
        'user_link',
        'visit_count',
        'share_url_display',
        'is_active',
        'created_at',
        'updated_at'
    ]
    
    list_filter = [
        'is_active',
        'created_at',
        'updated_at'
    ]
    
    search_fields = [
        'share_id',
        'user__anonymous_id',
        'user__email',
        'user__first_name',
        'user__last_name'
    ]
    
    readonly_fields = [
        'share_id',
        'visit_count',
        'share_url_display',
        'created_at',
        'updated_at',
        'total_visits_display'
    ]
    
    autocomplete_fields = ['user']
    
    ordering = ['-created_at']
    
    fieldsets = (
        (_('Share Link Information'), {
            'fields': (
                'share_id',
                'user',
                'is_active',
                'share_url_display'
            )
        }),
        (_('Statistics'), {
            'fields': (
                'visit_count',
                'total_visits_display'
            )
        }),
        (_('Timestamps'), {
            'fields': (
                'created_at',
                'updated_at'
            )
        })
    )
    
    def user_link(self, obj):
        """Display user with link to user admin"""
        if obj.user:
            url = reverse('admin:radio_crestin_appusers_change', args=[obj.user.id])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.user.anonymous_id or obj.user.email or f'User {obj.user.id}'
            )
        return '-'
    user_link.short_description = _('User')
    user_link.admin_order_field = 'user__anonymous_id'
    
    def share_url_display(self, obj):
        """Display the full share URL"""
        if obj:
            url = obj.get_full_url()
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                url,
                url
            )
        return '-'
    share_url_display.short_description = _('Share URL')
    
    def total_visits_display(self, obj):
        """Display total number of visit records"""
        if obj:
            count = obj.visits.count()
            if count > 0:
                url = reverse('admin:radio_crestin_sharelinkvisit_changelist') + f'?share_link__id__exact={obj.id}'
                return format_html(
                    '<a href="{}">{} visits</a>',
                    url,
                    count
                )
            return '0 visits'
        return '-'
    total_visits_display.short_description = _('Total Visit Records')
    
    def has_add_permission(self, request):
        """Disable manual creation of share links"""
        return False


@admin.register(ShareLinkVisit, site=superapp_admin_site)
class ShareLinkVisitAdmin(SuperAppModelAdmin):
    """Admin configuration for ShareLinkVisit model"""
    
    list_display = [
        'id',
        'share_link_display',
        'visitor_ip',
        'visitor_session_id',
        'visited_at',
        'visitor_referer_short'
    ]
    
    list_filter = [
        'visited_at',
        ('share_link', admin.RelatedOnlyFieldListFilter)
    ]
    
    search_fields = [
        'share_link__share_id',
        'visitor_ip',
        'visitor_session_id',
        'visitor_user_agent',
        'visitor_referer'
    ]
    
    readonly_fields = [
        'share_link',
        'visitor_ip',
        'visitor_user_agent',
        'visitor_referer',
        'visitor_session_id',
        'visited_at'
    ]
    
    ordering = ['-visited_at']
    
    date_hierarchy = 'visited_at'
    
    fieldsets = (
        (_('Visit Information'), {
            'fields': (
                'share_link',
                'visited_at'
            )
        }),
        (_('Visitor Details'), {
            'fields': (
                'visitor_ip',
                'visitor_session_id',
                'visitor_user_agent',
                'visitor_referer'
            )
        })
    )
    
    def share_link_display(self, obj):
        """Display share link with link to its admin"""
        if obj.share_link:
            url = reverse('admin:radio_crestin_sharelink_change', args=[obj.share_link.id])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.share_link.share_id
            )
        return '-'
    share_link_display.short_description = _('Share Link')
    share_link_display.admin_order_field = 'share_link__share_id'
    
    def visitor_referer_short(self, obj):
        """Display shortened version of referer URL"""
        if obj.visitor_referer:
            if len(obj.visitor_referer) > 50:
                return obj.visitor_referer[:50] + '...'
            return obj.visitor_referer
        return '-'
    visitor_referer_short.short_description = _('Referer')
    
    def has_add_permission(self, request):
        """Disable manual creation of visits"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable editing of visits"""
        return False