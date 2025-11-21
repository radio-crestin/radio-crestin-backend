from django.db import models
from django.utils.translation import gettext_lazy as _

from superapp.apps.storage.config import PublicS3Storage


class Artists(models.Model):
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    name = models.TextField(_("Name"))
    thumbnail = models.ImageField(
        _("Thumbnail"),
        storage=PublicS3Storage,
        upload_to='artists/',
        blank=True,
        null=True,
    )
    thumbnail_url = models.URLField(_("Thumbnail URL"), blank=True, null=True)
    dirty_metadata = models.BooleanField(_("Dirty Metadata"), default=False, help_text=_("Created from automatic metadata scraping (eligible for cleanup)"))

    class Meta:
        managed = True
        verbose_name = _("Artist")
        verbose_name_plural = _("Artists")
        db_table = 'artists'
        unique_together = (('name',),)
        ordering = ('name',)

    def __str__(self):
        return self.name or f"no name - id: {self.id}"

    def save(self, *args, **kwargs):
        if self.thumbnail:
            self.thumbnail_url = self.thumbnail.url
        super(Artists, self).save(*args, **kwargs)
