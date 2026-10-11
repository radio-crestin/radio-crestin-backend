from django.db import models
from django.utils.translation import gettext_lazy as _


class StationsNowPlayingHistory(models.Model):
    timestamp = models.DateTimeField(_("Timestamp"))
    # `timestamp` orders a station's rows and says when a row can still
    # appear; this is the song start the API shows for the row. They differ
    # for listener-count rows, which repeat the start of their song.
    song_started_at = models.DateTimeField(
        _("Song started at"),
        blank=True,
        null=True,
        help_text=_("When the song of this row started playing. Listener-count changes repeat the start of the song they belong to. Empty on rows written before this field existed, where the timestamp is the song start."),
    )
    station = models.ForeignKey(
        'Stations',
        verbose_name=_("Station"),
        on_delete=models.CASCADE,
        related_name='now_playing_history',
    )
    song = models.ForeignKey(
        'Songs',
        verbose_name=_("Song"),
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='played_history',
    )
    listeners = models.IntegerField(_("Listeners"), blank=True, null=True)

    # Multiple timestamp sources for song change detection
    id3_timestamp = models.DateTimeField(
        _("ID3 Metadata Timestamp"),
        blank=True,
        null=True,
        help_text=_("When ID3 stream metadata indicated a song change"),
    )
    scraper_timestamp = models.DateTimeField(
        _("Scraper Timestamp"),
        blank=True,
        null=True,
        help_text=_("When external metadata scraper detected a song change"),
    )
    timestamp_source = models.CharField(
        _("Timestamp Source"),
        max_length=20,
        blank=True,
        default='',
        help_text=_("Which source triggered this history entry (id3_metadata, scraper)"),
    )

    class Meta:
        managed = True
        verbose_name = _("Station Now Playing History")
        verbose_name_plural = _("Station Now Playing History")
        db_table = 'stations_now_playing_history'
        ordering = ('-timestamp',)
        indexes = [
            models.Index(fields=['station', '-timestamp'], name='idx_snph_station_ts'),
            models.Index(fields=['timestamp', 'station'], name='idx_snph_ts_station'),
        ]

    def __str__(self):
        return f"NowPlaying #{self.pk} ({self.timestamp})"

    @property
    def song_start(self):
        """The start of this row's song, as the API reports it."""
        return self.song_started_at or self.timestamp
