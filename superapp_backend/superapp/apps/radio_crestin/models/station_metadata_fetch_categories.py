from django.db import models
from django.utils.translation import gettext_lazy as _


class StationMetadataFetchCategories(models.Model):
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    slug = models.TextField(_("Slug"), unique=True)

    class Meta:
        managed = True
        verbose_name = _("Station Metadata Fetch Category")
        verbose_name_plural = _("Station Metadata Categories")
        db_table = 'station_metadata_fetch_categories'
        ordering = ('slug',)

    def __str__(self):
        return f"{self.slug}"