from django.db import models
from django.utils.translation import gettext_lazy as _
from .station_groups import StationGroups
from ...storage.config import get_public_storage


class MetadataTimestampSource(models.TextChoices):
    ID3_METADATA = 'id3_metadata', _('ID3 Stream Metadata')
    SCRAPER = 'scraper', _('External Scraper (periodic)')


class Stations(models.Model):
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    disabled = models.BooleanField(_("Disabled"), default=False)
    order = models.IntegerField(_("Order"), default=0) # deprecated, use station_order instead
    station_order = models.FloatField(_("Station Order"), default=0)
    slug = models.SlugField(_("Slug"))
    title = models.TextField(_("Title"))
    website = models.URLField(_("Website"))
    email = models.TextField(_("Email"), blank=True, null=False, default="")
    transcode_enabled = models.BooleanField(_("Live Transcoding"), default=True)
    stream_url = models.URLField(_("Stream URL"))

    # Metadata timestamp source configuration
    metadata_timestamp_source = models.CharField(
        _("Metadata Timestamp Source"),
        max_length=20,
        choices=MetadataTimestampSource.choices,
        default=MetadataTimestampSource.SCRAPER,
        help_text=_("Which detection method triggers metadata scraping: ID3 tags or periodic scraper interval"),
    )
    metadata_scrape_interval = models.IntegerField(
        _("Metadata Scrape Interval (seconds)"),
        default=30,
        help_text=_("How often to scrape metadata when using 'scraper' timestamp source"),
    )
    id3_metadata_delay_offset = models.FloatField(
        _("ID3 Metadata Delay Offset (seconds)"),
        default=0.0,
        help_text=_("Time offset to shift ID3 metadata timing (positive = delay, negative = advance)"),
    )
    config_version = models.PositiveIntegerField(
        _("Config Version"),
        default=1,
        help_text=_("Incremented on config changes to notify streaming pods to reload"),
    )
    thumbnail = models.ImageField(
        _("Thumbnail"),
        storage=get_public_storage,
        upload_to='stations/',
        blank=True,
        null=True,
    )
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
        ordering = ('station_order', 'title',)

    def __str__(self):
        return f"{self.title}"

    @property
    def generate_hls_stream(self):
        return self.transcode_enabled

    @generate_hls_stream.setter
    def generate_hls_stream(self, value):
        self.transcode_enabled = value

    def save(self, *args, **kwargs):
        self.order = round(self.station_order)
        super(Stations, self).save(*args, **kwargs)
        if self.thumbnail:
            self.thumbnail_url = self.thumbnail.url
            super(Stations, self).save(update_fields=['thumbnail_url'])
