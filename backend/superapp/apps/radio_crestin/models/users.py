from django.db import models
from django.utils.translation import gettext_lazy as _


class AppUsers(models.Model):
    # This model matches the existing authentication_user table structure
    password = models.CharField(max_length=128, blank=True, null=True)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.BooleanField(default=False)
    first_name = models.CharField(max_length=150, blank=True, null=True)
    last_name = models.CharField(max_length=150, blank=True, null=True)
    email = models.CharField(max_length=254, blank=True, null=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    # Custom fields added to the existing table
    anonymous_id = models.CharField(max_length=512, blank=True, null=True)
    anonymous_id_verified = models.DateTimeField(blank=True, null=True)
    email_verified = models.DateTimeField(blank=True, null=True)
    phone_number = models.CharField(max_length=255, blank=True, null=True)
    phone_number_verified = models.DateTimeField(blank=True, null=True)
    checkout_phone_number = models.CharField(max_length=255, blank=True, null=True)
    photo_url = models.CharField(max_length=255, blank=True, null=True)
    address = models.CharField(max_length=1024, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'app_users'
        verbose_name = _("App User")
        verbose_name_plural = _("App Users")

    def __str__(self):
        return f"App User {self.anonymous_id or self.email or self.id}"
