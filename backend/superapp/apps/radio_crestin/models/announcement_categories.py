from typing import Optional

from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from .announcement_validators import validate_public_slug

hex_color_validator = RegexValidator(
    r'^#[0-9A-Fa-f]{6}$',
    _("Enter a hex color such as #0F6E63."),
)


def _channel_luminance(channel: int) -> float:
    c = channel / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _relative_luminance(hex_color: str) -> float:
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * _channel_luminance(r) + 0.7152 * _channel_luminance(g) + 0.0722 * _channel_luminance(b)


def text_color_on(hex_color: str) -> str:
    """White or black, whichever contrasts more with `hex_color` (WCAG)."""
    luminance = _relative_luminance(hex_color)
    contrast_with_white = 1.05 / (luminance + 0.05)
    contrast_with_black = (luminance + 0.05) / 0.05
    return '#FFFFFF' if contrast_with_white >= contrast_with_black else '#000000'


class AnnouncementCategory(models.Model):
    """The colored tag shown on an announcement card (Community, Event, ...)."""

    slug = models.SlugField(_("Slug"), max_length=64, unique=True, validators=[validate_public_slug])
    name = models.CharField(_("Name"), max_length=64, help_text=_("Shown on the tag, in Romanian."))
    color = models.CharField(
        _("Color"), max_length=7, blank=True, default='', validators=[hex_color_validator],
        help_text=_("Empty uses the app's and website's default color."),
    )
    ordering = models.IntegerField(_("Ordering"), default=0)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    class Meta:
        managed = True
        db_table = 'announcement_categories'
        ordering = ('ordering', 'slug')
        verbose_name = _("Announcement Category")
        verbose_name_plural = _("Announcement Categories")

    def __str__(self):
        return self.name

    @property
    def text_color(self) -> Optional[str]:
        return text_color_on(self.color) if self.color else None
