from django.apps import apps
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import display
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from superapp.apps.admin_portal.helpers import SuperAppModelAdmin
from superapp.apps.admin_portal.sites import superapp_admin_site
from .models import (
    User,
)


class UserTypeFilter(SimpleListFilter):
    title = _('User Type')
    parameter_name = 'user_type'

    def lookups(self, request, model_admin):
        return (
            ('authenticated', _('Authenticated Users')),
            ('anonymous', _('Anonymous Users')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'authenticated':
            return queryset.filter(anonymous_id__isnull=True)
        elif self.value() == 'anonymous':
            return queryset.filter(anonymous_id__isnull=False)
        return queryset


@admin.register(User, site=superapp_admin_site)
class UserAdmin(BaseUserAdmin, SuperAppModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    search_fields = ["email", "first_name", "last_name", "phone_number", "anonymous_id"]
    list_display = [
        "display_header",
        "is_active",
        "display_staff",
        "display_superuser",
        "display_created",
    ]
    list_filter = [UserTypeFilter, "is_active", "is_staff", "is_superuser"]

    add_fieldsets = (
        (
            None,
            {
                "fields": (
                    "email",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
    fieldsets = (
        (None, {
            "fields": (
                "email",
                "email_verified",
                "phone_number",
                "phone_number_verified",
                "anonymous_id",
                "anonymous_id_verified",
                "password",
            )
        }),
        (
            _("Personal info"),
            {"fields": (
                ("first_name", "last_name"),
                "user_phone_number",
                "address",
                "photo_url",
            )},
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    filter_horizontal = (
        "groups",
        "user_permissions",
    )
    readonly_fields = ["last_login", "date_joined", "user_phone_number"]
    ordering = ["-created_at"]

    def user_phone_number(self, instance: User):
        return instance.phone_number or instance.checkout_phone_number or _("Not provided")

    @display(description=_("User"), header=True)
    def display_header(self, instance: User):
        return instance.full_name, str(instance)

    @display(description=_("Staff"), boolean=True)
    def display_staff(self, instance: User):
        return instance.is_staff

    @display(description=_("Superuser"), boolean=True)
    def display_superuser(self, instance: User):
        return instance.is_superuser

    @display(description=_("Created"))
    def display_created(self, instance: User):
        return instance.created_at


@admin.register(Group, site=superapp_admin_site)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


if apps.is_installed("allauth.account"):
    from allauth.account.admin import EmailConfirmationAdmin, EmailAddressAdmin
    from allauth.account.models import EmailConfirmation, EmailAddress

    if admin.site.is_registered(EmailAddress):
        superapp_admin_site.register(
            EmailAddress,
            (lambda: type('EmailAddressAdmin', (EmailAddressAdmin, SuperAppModelAdmin), {}))(),
        )

    if admin.site.is_registered(EmailConfirmation):
        superapp_admin_site.register(
            EmailConfirmation,
            (lambda: type('EmailConfirmationAdmin', (EmailConfirmationAdmin, SuperAppModelAdmin), {}))(),
        )

if apps.is_installed("allauth.usersessions"):
    from allauth.usersessions.admin import UserSessionAdmin
    from allauth.usersessions.models import UserSession

    if admin.site.is_registered(UserSession):
        superapp_admin_site.register(
            UserSession,
            (lambda: type('UserSessionAdmin', (UserSessionAdmin, SuperAppModelAdmin), {}))(),
        )

if apps.is_installed("allauth.mfa"):
    from allauth.mfa.admin import AuthenticatorAdmin
    from allauth.mfa.models import Authenticator

    if admin.site.is_registered(Authenticator):
        superapp_admin_site.register(
            Authenticator,
            (lambda: type('AuthenticatorAdmin', (AuthenticatorAdmin, SuperAppModelAdmin), {}))(),
        )

if apps.is_installed("allauth.socialaccount"):
    from allauth.socialaccount.admin import SocialAppAdmin, SocialTokenAdmin, SocialAccountAdmin
    from allauth.socialaccount.models import SocialApp, SocialToken, SocialAccount

    if admin.site.is_registered(SocialApp):
        superapp_admin_site.register(
            SocialApp,
            (lambda: type('SocialAppAdmin', (SocialAppAdmin, SuperAppModelAdmin), {}))(),
        )

    if admin.site.is_registered(SocialToken):
        superapp_admin_site.register(
            SocialToken,
            (lambda: type('SocialTokenAdmin', (SocialTokenAdmin, SuperAppModelAdmin), {}))(),
        )

    if admin.site.is_registered(SocialAccount):
        superapp_admin_site.register(
            SocialAccount,
            (lambda: type('SocialAccountAdmin', (SocialAccountAdmin, SuperAppModelAdmin), {}))(),
        )


if apps.is_installed("allauth.socialaccount.providers.sms"):
    from allauth.socialaccount.providers.sms.admin import SMSVerificationAdmin
    from allauth.socialaccount.providers.sms.models import SMSVerification

    if admin.site.is_registered(SMSVerification):
        superapp_admin_site.register(
            SMSVerification,
            (lambda: type('SMSVerificationAdmin', (SMSVerificationAdmin, SuperAppModelAdmin), {}))(),
        )

if apps.is_installed("allauth.socialaccount.providers.openid"):
    from allauth.socialaccount.providers.openid.admin import OpenIDStoreAdmin, OpenIDNonceAdmin
    from allauth.socialaccount.providers.openid.models import OpenIDStore, OpenIDNonce

    if admin.site.is_registered(OpenIDStore):
        superapp_admin_site.register(
            OpenIDStore,
            (lambda: type('OpenIDStoreAdmin', (OpenIDStoreAdmin, SuperAppModelAdmin), {}))(),
        )

    if admin.site.is_registered(OpenIDNonce):
        superapp_admin_site.register(
            OpenIDNonce,
            (lambda: type('OpenIDNonceAdmin', (OpenIDNonceAdmin, SuperAppModelAdmin), {}))(),
        )
