from django.db import models
from django.utils.translation import gettext_lazy as _


class StationsNowPlayingHistory(models.Model):
    timestamp = models.DateTimeField(_("Timestamp"))
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
        song_display = self.song if self.song else "No song"
        return f"{self.station} - {song_display} ({self.timestamp})"
