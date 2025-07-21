from django.db import models
from django.utils.translation import gettext_lazy as _


class AppUsers(models.Model):
    """
    Proxy/View model for authentication_user table to provide Hasura compatibility.
    This creates a 'users' table/view that references authentication.User.
    """
    # Copy all fields from authentication.User for compatibility
    password = models.CharField(_("password"), max_length=128, blank=True)
    last_login = models.DateTimeField(_("last login"), blank=True, null=True)
    is_superuser = models.BooleanField(_("superuser status"), default=False)
    first_name = models.CharField(_("first name"), max_length=150, blank=True)
    last_name = models.CharField(_("last name"), max_length=150, blank=True)
    email = models.EmailField(_("email address"), blank=True, null=True)
    is_staff = models.BooleanField(_("staff status"), default=True)
    is_active = models.BooleanField(_("active"), default=True)
    date_joined = models.DateTimeField(_("date joined"), auto_now_add=True)

    anonymous_id = models.CharField(_("Anonymous ID"), max_length=512, blank=True, null=True)
    anonymous_id_verified = models.DateTimeField(_("Anonymous ID verified"), blank=True, null=True)
    email_verified = models.DateTimeField(_("Email verified"), blank=True, null=True)
    phone_number = models.CharField(_("Phone number"), max_length=255, blank=True, null=True)
    phone_number_verified = models.DateTimeField(_("Phone number verified"), blank=True, null=True)
    checkout_phone_number = models.CharField(_("Checkout phone number"), max_length=255, blank=True, null=True)
    photo_url = models.CharField(max_length=255, blank=True, null=True)
    address = models.CharField(max_length=1024, blank=True, null=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    modified_at = models.DateTimeField(_("modified at"), auto_now=True)

    class Meta:
        managed = True  # This is now a managed table that syncs with authentication_user
        db_table = 'app_users'
        verbose_name = _("App User")
        verbose_name_plural = _("App Users")

    def __str__(self):
        return self.email or f"App User {self.pk}"
