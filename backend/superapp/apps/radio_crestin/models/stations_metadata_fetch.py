from django.db import models
from django.utils.translation import gettext_lazy as _


class StationsMetadataFetch(models.Model):
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    station = models.ForeignKey('Stations', verbose_name=_("Station"), on_delete=models.CASCADE, related_name='station_metadata_fetches')
    station_metadata_fetch_category = models.ForeignKey('StationMetadataFetchCategories', verbose_name=_("Category"), on_delete=models.CASCADE, related_name='station_metadata_fetches')
    priority = models.IntegerField(_("Priority"), default=1, help_text=_("Higher number = higher priority"))
    url = models.TextField(_("URL"))
    
    # Regex configuration fields for title/artist extraction
    split_character = models.CharField(_("Split Character"), max_length=10, default=" - ", help_text=_("Character(s) used to split artist and title"))
    station_name_regex = models.TextField(_("Station Name Regex"), blank=True, null=True, help_text=_("Regex pattern to remove station name from title (optional)"))
    artist_regex = models.TextField(_("Artist Regex"), blank=True, null=True, help_text=_("Regex pattern to extract artist (optional)"))
    title_regex = models.TextField(_("Title Regex"), blank=True, null=True, help_text=_("Regex pattern to extract title (optional)"))

    class Meta:
        managed = True
        verbose_name = _("Station Metadata Fetch")
        verbose_name_plural = _("Station Metadata Fetches")
        db_table = 'stations_metadata_fetch'
        ordering = ('station',)

    def __str__(self):
        return f"{self.station}-{self.url}"