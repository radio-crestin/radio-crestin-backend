from django.db import models
from django.utils.translation import gettext_lazy as _
from .artists import Artists


class Songs(models.Model):
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    name = models.TextField(_("Name"))
    artist = models.ForeignKey(Artists, verbose_name=_("Artist"), on_delete=models.CASCADE)
    thumbnail = models.ImageField(_("Thumbnail"), blank=True, null=True)
    thumbnail_url = models.URLField(_("Thumbnail URL"), blank=True, null=True)

    class Meta:
        managed = True
        verbose_name = _("Song")
        verbose_name_plural = _("Songs")
        db_table = 'songs'
        unique_together = (('name', 'artist'),)
        ordering = ('artist', 'name')

    def __str__(self):
        return f"{self.name}-{self.artist}"

    def save(self, *args, **kwargs):
        super(Songs, self).save(*args, **kwargs)
        if self.thumbnail:
            self.thumbnail_url = self.thumbnail.url
        super(Songs, self).save(*args, **kwargs)