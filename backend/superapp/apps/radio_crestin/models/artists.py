from django.db import models
from django.utils.translation import gettext_lazy as _


class Artists(models.Model):
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    name = models.TextField(_("Name"))
    thumbnail = models.ImageField(_("Thumbnail"), blank=True, null=True)
    thumbnail_url = models.URLField(_("Thumbnail URL"), blank=True, null=True)

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