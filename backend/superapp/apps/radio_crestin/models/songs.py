from django.db import models
from django.utils.translation import gettext_lazy as _
from .artists import Artists
from ...storage.config import get_public_storage


class Songs(models.Model):
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    name = models.TextField(_("Name"))
    artist = models.ForeignKey(Artists, verbose_name=_("Artist"), on_delete=models.CASCADE, null=True, blank=True)
    thumbnail = models.ImageField(
        _("Thumbnail"),
        storage=get_public_storage,
        upload_to='songs/',
        blank=True,
        null=True,
    )
    thumbnail_url = models.URLField(_("Thumbnail URL"), blank=True, null=True)
    dirty_metadata = models.BooleanField(_("Dirty Metadata"), default=False, help_text=_("Created from automatic metadata scraping (eligible for cleanup)"))

    class Meta:
        managed = True
        verbose_name = _("Song")
        verbose_name_plural = _("Songs")
        db_table = 'songs'
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'artist'],
                name='unique_song_artist',
                condition=models.Q(artist__isnull=False)
            ),
            models.UniqueConstraint(
                fields=['name'],
                name='unique_song_no_artist',
                condition=models.Q(artist__isnull=True)
            )
        ]
        ordering = ('artist', 'name')

    def __str__(self):
        artist_name = self.artist.name if self.artist else "Unknown Artist"
        return f"{self.name} - {artist_name}"

    def save(self, *args, **kwargs):
        if self.thumbnail:
            self.thumbnail_url = self.thumbnail.url
        super(Songs, self).save(*args, **kwargs)
