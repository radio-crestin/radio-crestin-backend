from django.db import models
from django.utils.translation import gettext_lazy as _


class StationsMetadataFetch(models.Model):
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    station = models.ForeignKey('Stations', verbose_name=_("Station"), on_delete=models.CASCADE, related_name='station_metadata_fetches')
    station_metadata_fetch_category = models.ForeignKey('StationMetadataFetchCategories', verbose_name=_("Category"), on_delete=models.CASCADE, related_name='station_metadata_fetches')
    order = models.IntegerField(_("Order"))
    url = models.TextField(_("URL"))

    class Meta:
        managed = True
        verbose_name = _("Station Metadata Fetch")
        verbose_name_plural = _("Station Metadata Fetches")
        db_table = 'stations_metadata_fetch'
        ordering = ('station',)

    def __str__(self):
        return f"{self.station}-{self.url}"