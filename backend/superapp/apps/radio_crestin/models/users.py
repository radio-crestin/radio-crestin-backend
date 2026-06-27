from django.db import models
from django.utils.translation import gettext_lazy as _


class AppUsers(models.Model):
    # This model matches the existing authentication_user table structure
    password = models.CharField(max_length=128, blank=True, null=False, default="")
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.BooleanField(default=False)
    first_name = models.CharField(max_length=150, blank=True, null=True)
    last_name = models.CharField(max_length=150, blank=True, null=True)
    email = models.CharField(max_length=254, blank=True, null=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    # Custom fields added to the existing table
    anonymous_id = models.CharField(max_length=512, blank=True, null=True, unique=True)
    anonymous_id_verified = models.DateTimeField(blank=True, null=True)
    email_verified = models.DateTimeField(blank=True, null=True)
    phone_number = models.CharField(max_length=255, blank=True, null=True)
    phone_number_verified = models.DateTimeField(blank=True, null=True)
    checkout_phone_number = models.CharField(max_length=255, blank=True, null=True)
    photo_url = models.CharField(max_length=255, blank=True, null=True)
    address = models.CharField(max_length=1024, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    # Device registration details — upserted by the mobile app on every launch
    # via POST /api/v1/devices/register/, keyed by anonymous_id. The columns
    # below are the queryable essentials; the full raw snapshot (brand, screen
    # size, ABIs, etc.) is kept in device_info. The public IP is captured
    # server-side from the request, never trusted from the client body.
    device_platform = models.CharField(_("Device platform"), max_length=64, blank=True, null=True)
    device_model = models.CharField(_("Device model"), max_length=255, blank=True, null=True)
    device_manufacturer = models.CharField(_("Device manufacturer"), max_length=255, blank=True, null=True)
    device_os_version = models.CharField(_("OS version"), max_length=64, blank=True, null=True)
    device_app_version = models.CharField(_("App version"), max_length=64, blank=True, null=True)
    device_build_number = models.CharField(_("App build number"), max_length=64, blank=True, null=True)
    device_locale = models.CharField(_("Locale"), max_length=64, blank=True, null=True)
    device_timezone = models.CharField(_("Timezone"), max_length=64, blank=True, null=True)
    device_is_physical = models.BooleanField(_("Is physical device"), blank=True, null=True)
    device_fcm_token = models.TextField(_("FCM push token"), blank=True, null=True)
    device_last_ip = models.GenericIPAddressField(_("Last IP address"), blank=True, null=True)
    device_info = models.JSONField(_("Raw device info"), blank=True, null=True)
    device_first_seen_at = models.DateTimeField(_("Device first seen at"), blank=True, null=True)
    device_last_seen_at = models.DateTimeField(_("Device last seen at"), blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'app_users'
        verbose_name = _("App User")
        verbose_name_plural = _("App Users")

    def __str__(self):
        return f"App User {self.anonymous_id or self.email or self.id}"
