from django.db import models
from django.utils.translation import gettext_lazy as _


class AppUsers(models.Model):
    anonymous_id = models.CharField(_("Anonymous ID"), max_length=512, unique=True, help_text=_("Unique identifier for the user, used for analytics and tracking."))

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    modified_at = models.DateTimeField(_("modified at"), auto_now=True)

    class Meta:
        managed = True  # This is now a managed table that syncs with authentication_user
        db_table = 'app_users'
        verbose_name = _("App User")
        verbose_name_plural = _("App Users")

    def __str__(self):
        return f"App User {self.anonymous_id}"
