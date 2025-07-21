from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from superapp.apps.admin_portal.admin import SuperAppModelAdmin
from superapp.apps.admin_portal.sites import superapp_admin_site
from ..models import AppUsers


@admin.register(AppUsers, site=superapp_admin_site)
class AppUsersAdmin(SuperAppModelAdmin):
    list_display = ['email', 'first_name', 'last_name', 'verification_status', 'is_active', 'date_joined', 'last_login']
    list_filter = ['is_active', 'is_staff', 'is_superuser', 'email_verified', 'phone_number_verified', 'date_joined']
    search_fields = ['email', 'first_name', 'last_name', 'phone_number', 'anonymous_id']
    readonly_fields = ['created_at', 'modified_at', 'date_joined', 'last_login', 'photo_preview', 'verification_status_detail']
    date_hierarchy = 'date_joined'
    ordering = ['-date_joined']
    
    fieldsets = (
        (_("Personal Info"), {
            'fields': ('first_name', 'last_name', 'email', 'photo_url', 'photo_preview')
        }),
        (_("Contact Information"), {
            'fields': ('phone_number', 'checkout_phone_number', 'address')
        }),
        (_("Verification"), {
            'fields': ('email_verified', 'phone_number_verified', 'anonymous_id', 'anonymous_id_verified', 'verification_status_detail')
        }),
        (_("Permissions"), {
            'fields': ('is_active', 'is_staff', 'is_superuser'),
        }),
        (_("Important dates"), {
            'fields': ('last_login', 'date_joined', 'created_at', 'modified_at'),
            'classes': ('collapse',)
        }),
    )
    
    def verification_status(self, obj):
        statuses = []
        if obj.email_verified:
            statuses.append(format_html('<span style="color: green;">✓ Email</span>'))
        else:
            statuses.append(format_html('<span style="color: gray;">○ Email</span>'))
            
        if obj.phone_number_verified:
            statuses.append(format_html('<span style="color: green;">✓ Phone</span>'))
        elif obj.phone_number:
            statuses.append(format_html('<span style="color: gray;">○ Phone</span>'))
            
        return mark_safe(' '.join(statuses)) if statuses else _("Unverified")
    verification_status.short_description = _("Verification")
    
    def verification_status_detail(self, obj):
        details = []
        if obj.email_verified:
            details.append(format_html('<div>✓ Email verified: {}</div>', obj.email_verified.strftime('%Y-%m-%d %H:%M')))
        else:
            details.append(format_html('<div>○ Email not verified</div>'))
            
        if obj.phone_number_verified:
            details.append(format_html('<div>✓ Phone verified: {}</div>', obj.phone_number_verified.strftime('%Y-%m-%d %H:%M')))
        elif obj.phone_number:
            details.append(format_html('<div>○ Phone not verified</div>'))
            
        if obj.anonymous_id_verified:
            details.append(format_html('<div>✓ Anonymous ID verified: {}</div>', obj.anonymous_id_verified.strftime('%Y-%m-%d %H:%M')))
            
        return mark_safe('<div style="line-height: 1.5;">' + ''.join(details) + '</div>')
    verification_status_detail.short_description = _("Verification Details")
    
    def photo_preview(self, obj):
        if obj.photo_url:
            return format_html(
                '<img src="{}" width="100" height="100" style="object-fit: cover; border-radius: 50%;" />',
                obj.photo_url
            )
        return _("No photo")
    photo_preview.short_description = _("Photo")
    
    def has_delete_permission(self, request, obj=None):
        # Prevent accidental deletion of users
        return False