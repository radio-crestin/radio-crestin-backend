from django.db import models
from django.utils.translation import gettext_lazy as _
from .station_groups import StationGroups


class Stations(models.Model):
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    disabled = models.BooleanField(_("Disabled"), default=False)
    order = models.IntegerField(_("Order")) # deprecated, use station_order instead
    station_order = models.FloatField(_("Station Order"))
    slug = models.SlugField(_("Slug"))
    title = models.TextField(_("Title"))
    website = models.URLField(_("Website"))
    email = models.TextField(_("Email"), blank=True, null=False, default="")
    generate_hls_stream = models.BooleanField(_("Generate HLS Stream"), default=True)
    stream_url = models.URLField(_("Stream URL"))
    thumbnail = models.ImageField(_("Thumbnail"), blank=True, null=True)
    thumbnail_url = models.URLField(_("Thumbnail URL"), blank=True, null=True)
    description = models.TextField(_("Description"), blank=True, null=True)
    description_action_title = models.TextField(_("Description Action Title"), blank=True, null=True)
    description_link = models.URLField(_("Description Link"), blank=True, null=True)
    rss_feed = models.URLField(_("RSS Feed"), blank=True, null=True)
    feature_latest_post = models.BooleanField(_("Feature Latest Post"), default=True, blank=True, null=True)
    facebook_page_id = models.TextField(_("Facebook Page ID"), blank=True, null=True)
    check_uptime = models.BooleanField(_("Check Uptime"), default=True)

    latest_station_uptime = models.ForeignKey('StationsUptime', verbose_name=_("Latest Station Uptime"), on_delete=models.SET_NULL, blank=True, null=True, related_name='latest_for_stations')
    latest_station_now_playing = models.ForeignKey('StationsNowPlaying', verbose_name=_("Latest Now Playing"), on_delete=models.SET_NULL, blank=True, null=True, related_name='latest_for_stations')

    groups = models.ManyToManyField(
        StationGroups,
        through='StationToStationGroup',
        related_name='stations',
        verbose_name=_("Groups")
    )

    class Meta:
        managed = True
        verbose_name = _("Station")
        verbose_name_plural = _("Stations")
        db_table = 'stations'
        ordering = ('order', 'title',)

    def __str__(self):
        return f"{self.title}"

    def save(self, *args, **kwargs):
        super(Stations, self).save(*args, **kwargs)
        self.order = round(self.station_order)
        if self.thumbnail:
            self.thumbnail_url = self.thumbnail.url
        super(Stations, self).save(*args, **kwargs)
