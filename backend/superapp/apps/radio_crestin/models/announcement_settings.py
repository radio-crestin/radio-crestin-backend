import secrets

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class RotationMode(models.TextChoices):
    FIXED = 'fixed', _('Fixed: server order')
    ROTATE = 'rotate', _('Rotate: next one first on each load')
    RANDOM = 'random', _('Random first, then server order')


WEBSITE_PREVIEW_URL = 'https://www.radiocrestin.ro/?anunturi-preview={token}'
APP_PREVIEW_URL = 'radiocrestin://anunturi-preview?token={token}'


def new_preview_token() -> str:
    return secrets.token_urlsafe(24)


class AnnouncementSettings(models.Model):
    """How clients rotate announcements (single row)."""

    rotation_mode = models.CharField(
        _("Rotation mode"), max_length=16, choices=RotationMode.choices, default=RotationMode.ROTATE,
    )
    autoplay_seconds = models.PositiveSmallIntegerField(
        _("Autoplay seconds"), default=8, validators=[MinValueValidator(2), MaxValueValidator(120)],
        help_text=_("Seconds each announcement stays before the card moves to the next one."),
    )
    max_per_load = models.PositiveSmallIntegerField(
        _("Max announcements per load"), default=5, validators=[MinValueValidator(1), MaxValueValidator(50)],
    )
    preview_token = models.CharField(
        _("Preview token"), max_length=64, default=new_preview_token,
        help_text=_("Lets the preview links show announcements with the Preview status. Rotate it to revoke old links."),
    )
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    class Meta:
        managed = True
        db_table = 'announcement_settings'
        verbose_name = _("Announcement Settings")
        verbose_name_plural = _("Announcement Settings")

    def __str__(self):
        return f"{self.get_rotation_mode_display()} · {self.autoplay_seconds}s · max {self.max_per_load}"

    @classmethod
    def load(cls) -> 'AnnouncementSettings':
        """The single settings row, created on first use."""
        return cls.objects.order_by('pk').first() or cls.objects.create()

    @property
    def website_preview_url(self) -> str:
        return WEBSITE_PREVIEW_URL.format(token=self.preview_token)

    @property
    def app_preview_url(self) -> str:
        return APP_PREVIEW_URL.format(token=self.preview_token)
