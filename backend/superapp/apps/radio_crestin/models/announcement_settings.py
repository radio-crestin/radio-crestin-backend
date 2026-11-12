import secrets

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class RotationMode(models.TextChoices):
    FIXED = 'fixed', _('Fixed: server order')
    ROTATE = 'rotate', _('Rotate: next one first on each load')
    RANDOM = 'random', _('Random first, then server order')


WEBSITE_PREVIEW_URL = 'https://www.radiocrestin.ro/?anunturi-preview={token}'
APP_PREVIEW_URL = 'radiocrestin://anunturi-preview?token={token}'


AUTOPLAY_MIN_SECONDS, AUTOPLAY_MAX_SECONDS = 3, 60


def validate_autoplay_seconds(value: int):
    if value and not AUTOPLAY_MIN_SECONDS <= value <= AUTOPLAY_MAX_SECONDS:
        raise ValidationError(
            _('Use 0 (off) or %(min)s to %(max)s seconds.'),
            params={'min': AUTOPLAY_MIN_SECONDS, 'max': AUTOPLAY_MAX_SECONDS}, code='invalid_autoplay',
        )


def new_preview_token() -> str:
    return secrets.token_urlsafe(24)


class AnnouncementSettings(models.Model):
    """How clients rotate announcements (single row)."""

    rotation_mode = models.CharField(
        _("Rotation mode"), max_length=16, choices=RotationMode.choices, default=RotationMode.ROTATE,
        help_text=_(
            "Which announcement each visit starts with. Fixed: always the first in the list. Rotate: the next "
            "one on every visit, so each gets its turn. Random: any of them. The order itself is the "
            "drag-and-drop order of the Announcements list."
        ),
    )
    autoplay_seconds = models.PositiveSmallIntegerField(
        _("Move on by itself after (seconds)"), default=0, validators=[validate_autoplay_seconds],
        help_text=_(
            "0 keeps it off: people page through the announcements themselves. Otherwise 3 to 60: the card "
            "moves to the next announcement after this many seconds, until someone pages or closes one, "
            "and stops at the last."
        ),
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
        autoplay = f'{self.autoplay_seconds}s' if self.autoplay_seconds else 'no autoplay'
        return f"{self.get_rotation_mode_display()} · {autoplay} · max {self.max_per_load}"

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
