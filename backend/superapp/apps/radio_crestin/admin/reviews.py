from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from superapp.apps.admin_portal.admin import SuperAppModelAdmin
from superapp.apps.admin_portal.sites import superapp_admin_site
from ..models import Reviews


@admin.register(Reviews, site=superapp_admin_site)
class ReviewsAdmin(SuperAppModelAdmin):
    list_display = ['station', 'ip_address', 'user_identifier', 'stars_display', 'message_preview', 'verified_status', 'created_at']
    list_filter = ['stars', 'verified', 'created_at', 'station']
    search_fields = ['ip_address', 'user_identifier', 'station__title', 'message', 'user__email', 'user__anonymous_id']
    autocomplete_fields = ['user', 'station']
    readonly_fields = ['created_at', 'updated_at', 'stars_display', 'ip_address']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    actions = ['verify_reviews', 'unverify_reviews']

    fieldsets = (
        (_("Review Details"), {
            'fields': ('station', 'stars', 'stars_display', 'message')
        }),
        (_("Reviewer Info"), {
            'fields': ('ip_address', 'user_identifier', 'user')
        }),
        (_("Status"), {
            'fields': ('verified',)
        }),
        (_("Timestamps"), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def stars_display(self, obj):
        filled_stars = '★' * obj.stars
        empty_stars = '☆' * (5 - obj.stars)
        color = '#FFD700' if obj.stars >= 4 else '#FFA500' if obj.stars >= 2 else '#FF6347'
        return format_html(
            '<span style="color: {}; font-size: 1.2em;">{}{}</span> <small>({})</small>',
            color, filled_stars, empty_stars, obj.stars
        )
    stars_display.short_description = _("Rating")
    stars_display.admin_order_field = 'stars'
    
    def message_preview(self, obj):
        if obj.message:
            truncated = obj.message[:100] + '...' if len(obj.message) > 100 else obj.message
            return truncated
        return _("No message")
    message_preview.short_description = _("Message")
    
    def verified_status(self, obj):
        if obj.verified:
            return format_html('<span style="color: green;">✓</span> {}'.format(_("Verified")))
        else:
            return format_html('<span style="color: gray;">○</span> {}'.format(_("Unverified")))
    verified_status.short_description = _("Status")
    verified_status.admin_order_field = 'verified'
    
    def verify_reviews(self, request, queryset):
        updated = queryset.update(verified=True)
        self.message_user(request, f"{updated} review(s) have been verified.")
    verify_reviews.short_description = _("Verify selected reviews")
    
    def unverify_reviews(self, request, queryset):
        updated = queryset.update(verified=False)
        self.message_user(request, f"{updated} review(s) have been unverified.")
    unverify_reviews.short_description = _("Unverify selected reviews")
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'station')