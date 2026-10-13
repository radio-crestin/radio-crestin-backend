from django.db import models
from django.utils.translation import gettext_lazy as _


class SongThumbnailChecks(models.Model):
    """A song thumbnail URL, downloaded once and compared with the
    placeholder images (assets/placeholder_thumbnails/)."""

    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    url = models.URLField(_("URL"), unique=True)
    sha256 = models.CharField(_("SHA-256"), max_length=64)
    is_placeholder = models.BooleanField(
        _("Is placeholder"),
        help_text=_("The file is a station or site logo, not the song's cover"),
    )

    class Meta:
        managed = True
        verbose_name = _("Song Thumbnail Check")
        verbose_name_plural = _("Song Thumbnail Checks")
        db_table = 'song_thumbnail_checks'
        ordering = ('-created_at',)

    def __str__(self):
        return self.url
