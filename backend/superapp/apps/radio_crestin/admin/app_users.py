import unfold
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse, reverse_lazy
from django.utils.safestring import mark_safe
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect

from superapp.apps.admin_portal.admin import SuperAppModelAdmin
from superapp.apps.admin_portal.sites import superapp_admin_site
from ..models import AppUsers


class IsAnonymousFilter(admin.SimpleListFilter):
    title = _('User Type')
    parameter_name = 'user_type'

    def lookups(self, request, model_admin):
        return (
            ('anonymous', _('Anonymous Users')),
            ('registered', _('Registered Users')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'anonymous':
            return queryset.filter(Q(email__isnull=True) | Q(email=''), anonymous_id__isnull=False)
        elif self.value() == 'registered':
            return queryset.filter(email__isnull=False).exclude(email='')
        return queryset


@admin.register(AppUsers, site=superapp_admin_site)
class AppUsersAdmin(SuperAppModelAdmin):
    list_display = ['id', 'email', 'anonymous_id', 'user_type_display', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at', IsAnonymousFilter]
    search_fields = ['email', 'anonymous_id']
    readonly_fields = ['created_at', 'modified_at', 'date_joined']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    actions_list = [
        "delete_anonymous_users",
    ]
    
    fieldsets = (
        (_("User Info"), {
            'fields': ('email', 'first_name', 'last_name', 'anonymous_id')
        }),
        (_("Status"), {
            'fields': ('is_active', 'is_staff', 'is_superuser')
        }),
        (_("Contact Info"), {
            'fields': ('phone_number', 'checkout_phone_number', 'address'),
            'classes': ('collapse',)
        }),
        (_("Verification"), {
            'fields': ('email_verified', 'phone_number_verified', 'anonymous_id_verified'),
            'classes': ('collapse',)
        }),
        (_("Timestamps"), {
            'fields': ('created_at', 'modified_at', 'date_joined', 'last_login'),
            'classes': ('collapse',)
        }),
    )
    
    def user_type_display(self, obj):
        """Display whether user is anonymous or registered"""
        if obj.email and obj.email.strip():
            return _('Registered')
        elif obj.anonymous_id:
            return _('Anonymous')
        return _('Unknown')
    user_type_display.short_description = _('User Type')
    
    @unfold.decorators.action(description=_("Delete all anonymous users"))
    def delete_anonymous_users(self, request):
        """Bulk action to delete all anonymous users (respects current filters)"""
        # Get the current queryset with applied filters
        changelist = self.get_changelist_instance(request)
        queryset = changelist.get_queryset(request)
        
        # Filter to only anonymous users from the current queryset
        anonymous_users = queryset.filter(Q(email__isnull=True) | Q(email=''), anonymous_id__isnull=False)
        count = anonymous_users.count()
        
        if count == 0:
            self.message_user(request, _('No anonymous users found with current filters.'), messages.WARNING)
        else:
            # Delete the anonymous users
            anonymous_users.delete()
            self.message_user(
                request,
                _(f'{count} anonymous user{"s" if count != 1 else ""} deleted successfully.'),
                messages.SUCCESS
            )
        
        return redirect(reverse_lazy("admin:radio_crestin_appusers_changelist"))
    
    def has_delete_permission(self, request, obj=None):
        # Allow deletion of users
        return True