from django.db import models


class Artists(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    name = models.TextField()
    thumbnail = models.ImageField(blank=True, null=True,)
    thumbnail_url = models.URLField(blank=True, null=True,)

    class Meta:
        managed = False
        verbose_name = "Artist"
        verbose_name_plural = "Artists"
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    name = models.TextField()
    artist = models.ForeignKey(Artists, on_delete=models.CASCADE)
    thumbnail = models.ImageField(blank=True, null=True,)
    thumbnail_url = models.URLField(blank=True, null=True,)

    class Meta:
        managed = False
        verbose_name = "Song"
        verbose_name_plural = "Songs"
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField()
    name = models.TextField(unique=True)
    order = models.FloatField(default=0)

    class Meta:
        managed = False
        verbose_name = "Station Group"
        verbose_name_plural = "Station Groups"
        db_table = 'station_groups'
        ordering = ('order',)

    def __str__(self):
        return f"{self.name} (order: {self.order})"


class StationMetadataFetchCategories(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.TextField(unique=True)

    class Meta:
        managed = False
        verbose_name = "Station Metadata Fetch Category"
        verbose_name_plural = "Station Metadata Categories"
        db_table = 'station_metadata_fetch_categories'
        ordering = ('slug',)

    def __str__(self):
        return f"{self.slug}"


class StationToStationGroup(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    station = models.ForeignKey('Stations', null=True, on_delete=models.SET_NULL)
    group = models.ForeignKey(StationGroups, null=True, on_delete=models.SET_NULL)
    order = models.FloatField(blank=True, null=True, default=0)

    class Meta:
        managed = False
        db_table = 'station_to_station_group'
        unique_together = (('station', 'group'),)
        ordering = ('group',)

    def __str__(self):
        return f"{self.station}-{self.group}"


class Stations(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    order = models.FloatField()
    slug = models.SlugField()
    title = models.TextField()
    website = models.URLField()
    email = models.TextField(blank=True, null=True, )
    generate_hls_stream = models.BooleanField(default=True)
    stream_url = models.URLField()
    thumbnail = models.ImageField(blank=True, null=True,)
    thumbnail_url = models.URLField(blank=True, null=True,)
    description = models.TextField(blank=True, null=True,)
    description_action_title = models.TextField(blank=True, null=True,)
    description_link = models.URLField(blank=True, null=True,)
    rss_feed = models.URLField(blank=True, null=True,)
    feature_latest_post = models.BooleanField(default=True, blank=True, null=True,)
    facebook_page_id = models.TextField(blank=True, null=True,)

    latest_station_uptime = models.ForeignKey('StationsUptime', on_delete=models.SET_NULL, blank=True, null=True)
    latest_station_now_playing = models.ForeignKey('StationsNowPlaying', on_delete=models.SET_NULL, blank=True, null=True)

    groups = models.ManyToManyField(
        'StationGroups',
        through='StationToStationGroup',
        related_name='stations',
    )

    class Meta:
        managed = False
        verbose_name = "Station"
        verbose_name_plural = "Stations"
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
        ('HLS', 'HLS'),
        ('proxied_stream', 'Proxied Stream'),
        ('direct_stream', 'Direct Stream'),
    ]

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    station = models.ForeignKey('Stations', null=True, on_delete=models.SET_NULL)
    stream_url = models.TextField()
    order = models.FloatField(blank=True, null=True, default=0)
    type = models.TextField(choices=STREAM_TYPES)

    class Meta:
        managed = False
        db_table = 'station_streams'
        unique_together = (('station', 'stream_url'),)
        ordering = ('station', 'order',)

    def __str__(self):
        return f"{self.station}->{self.stream_url}"

class StationsMetadataFetch(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    station = models.ForeignKey(Stations, on_delete=models.SET_NULL, blank=True, null=True)
    station_metadata_fetch_category = models.ForeignKey(StationMetadataFetchCategories, null=True, on_delete=models.SET_NULL)
    order = models.IntegerField()
    url = models.TextField()

    class Meta:
        managed = False
        verbose_name = "Station Metadata Fetch"
        verbose_name_plural = "Station Metadata Fetches"
        db_table = 'stations_metadata_fetch'
        ordering = ('station',)

    def __str__(self):
        return f"{self.station}-{self.url}"


class Posts(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    title = models.TextField()
    link = models.TextField()
    description = models.TextField(null=True, blank=True)
    published = models.DateTimeField()
    station = models.ForeignKey('Stations', models.CASCADE)

    class Meta:
        managed = False
        verbose_name = "Post"
        verbose_name_plural = "Posts"
        db_table = 'posts'
        ordering = ('-published',)

    def __str__(self):
        return f"{self.station}-{self.title}"


class StationsNowPlaying(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    timestamp = models.DateTimeField()
    station = models.ForeignKey(Stations, on_delete=models.SET_NULL, blank=True, null=True)
    song = models.ForeignKey(Songs, on_delete=models.SET_NULL, blank=True, null=True)
    raw_data = models.JSONField()
    error = models.JSONField(blank=True, null=True)
    listeners = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'stations_now_playing'
        ordering = ('-timestamp',)

    def __str__(self):
        return f"{self.station} - {self.song} ({self.timestamp})"


class StationsUptime(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    timestamp = models.DateTimeField()
    station = models.ForeignKey(Stations, null=True, on_delete=models.SET_NULL)
    is_up = models.BooleanField()
    latency_ms = models.IntegerField()
    raw_data = models.JSONField()

    class Meta:
        managed = False
        db_table = 'stations_uptime'
        ordering = ('-timestamp',)

    def __str__(self):
        return f"{self.station} is {'up' if self.is_up else 'down'} - {self.latency_ms}ms  ({self.timestamp})"
