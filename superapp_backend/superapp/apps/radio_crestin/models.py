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
        super(Artists, self).save(*args, **kwargs)
        if self.thumbnail:
            self.thumbnail_url = self.thumbnail.url
        super(Artists, self).save(*args, **kwargs)


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


class StationGroups(models.Model):
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    slug = models.SlugField(_("Slug"))
    name = models.TextField(_("Name"), unique=True)
    order = models.FloatField(_("Order"), default=0)

    class Meta:
        managed = True
        verbose_name = _("Station Group")
        verbose_name_plural = _("Station Groups")
        db_table = 'station_groups'
        ordering = ('order',)

    def __str__(self):
        return f"{self.name} (order: {self.order})"


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


class StationToStationGroup(models.Model):
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    station = models.ForeignKey('Stations', verbose_name=_("Station"), null=True, on_delete=models.SET_NULL)
    group = models.ForeignKey(StationGroups, verbose_name=_("Group"), null=True, on_delete=models.SET_NULL)
    order = models.FloatField(_("Order"), blank=True, null=True, default=0)

    class Meta:
        managed = True
        verbose_name = _("Station to Group Relationship")
        verbose_name_plural = _("Station to Group Relationships")
        db_table = 'station_to_station_group'
        unique_together = (('station', 'group'),)
        ordering = ('group',)

    def __str__(self):
        return f"{self.station}-{self.group}"


class Stations(models.Model):
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    disabled = models.BooleanField(_("Disabled"), default=False)
    order = models.FloatField(_("Order"))
    slug = models.SlugField(_("Slug"))
    title = models.TextField(_("Title"))
    website = models.URLField(_("Website"))
    email = models.TextField(_("Email"), blank=True, null=True)
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

    latest_station_uptime = models.ForeignKey('StationsUptime', verbose_name=_("Latest Station Uptime"), on_delete=models.SET_NULL, blank=True, null=True)
    latest_station_now_playing = models.ForeignKey('StationsNowPlaying', verbose_name=_("Latest Now Playing"), on_delete=models.SET_NULL, blank=True, null=True)

    groups = models.ManyToManyField(
        'StationGroups',
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
        if self.thumbnail:
            self.thumbnail_url = self.thumbnail.url
        super(Stations, self).save(*args, **kwargs)


class StationStreams(models.Model):
    STREAM_TYPES = [
        ('HLS', _('HLS')),
        ('proxied_stream', _('Proxied Stream')),
        ('direct_stream', _('Direct Stream')),
    ]

    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    station = models.ForeignKey('Stations', verbose_name=_("Station"), null=True, on_delete=models.SET_NULL)
    stream_url = models.TextField(_("Stream URL"))
    order = models.FloatField(_("Order"), blank=True, null=True, default=0)
    type = models.TextField(_("Type"), choices=STREAM_TYPES)

    class Meta:
        managed = True
        verbose_name = _("Station Stream")
        verbose_name_plural = _("Station Streams")
        db_table = 'station_streams'
        unique_together = (('station', 'stream_url'),)
        ordering = ('station', 'order',)

    def __str__(self):
        return f"{self.station}->{self.stream_url}"


class StationsMetadataFetch(models.Model):
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    station = models.ForeignKey(Stations, verbose_name=_("Station"), on_delete=models.SET_NULL, blank=True, null=True)
    station_metadata_fetch_category = models.ForeignKey(StationMetadataFetchCategories, verbose_name=_("Category"), null=True, on_delete=models.SET_NULL)
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


class Posts(models.Model):
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    title = models.TextField(_("Title"))
    link = models.TextField(_("Link"))
    description = models.TextField(_("Description"), null=True, blank=True)
    published = models.DateTimeField(_("Published"))
    station = models.ForeignKey('Stations', verbose_name=_("Station"), on_delete=models.CASCADE)

    class Meta:
        managed = True
        verbose_name = _("Post")
        verbose_name_plural = _("Posts")
        db_table = 'posts'
        ordering = ('-published',)

    def __str__(self):
        return f"{self.station}-{self.title}"


class StationsNowPlaying(models.Model):
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    timestamp = models.DateTimeField(_("Timestamp"))
    station = models.ForeignKey(Stations, verbose_name=_("Station"), on_delete=models.SET_NULL, blank=True, null=True)
    song = models.ForeignKey(Songs, verbose_name=_("Song"), on_delete=models.SET_NULL, blank=True, null=True)
    raw_data = models.JSONField(_("Raw Data"))
    error = models.JSONField(_("Error"), blank=True, null=True)
    listeners = models.IntegerField(_("Listeners"), blank=True, null=True)

    class Meta:
        managed = True
        verbose_name = _("Station Now Playing")
        verbose_name_plural = _("Station Now Playing")
        db_table = 'stations_now_playing'
        ordering = ('-timestamp',)

    def __str__(self):
        return f"{self.station} - {self.song} ({self.timestamp})"


class StationsUptime(models.Model):
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    timestamp = models.DateTimeField(_("Timestamp"))
    station = models.ForeignKey(Stations, verbose_name=_("Station"), null=True, on_delete=models.SET_NULL)
    is_up = models.BooleanField(_("Is Up"))
    latency_ms = models.IntegerField(_("Latency (ms)"))
    raw_data = models.JSONField(_("Raw Data"))

    class Meta:
        managed = True
        verbose_name = _("Station Uptime")
        verbose_name_plural = _("Station Uptime")
        db_table = 'stations_uptime'
        ordering = ('-timestamp',)

    def __str__(self):
        return f"{self.station} is {'up' if self.is_up else 'down'} - {self.latency_ms}ms  ({self.timestamp})"