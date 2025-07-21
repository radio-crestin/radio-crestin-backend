from django.db import models
from django.utils.translation import gettext_lazy as _


class StationsNowPlaying(models.Model):
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    timestamp = models.DateTimeField(_("Timestamp"))
    station = models.OneToOneField('Stations', verbose_name=_("Station"), on_delete=models.CASCADE, related_name='now_playing')
    song = models.ForeignKey('Songs', verbose_name=_("Song"), on_delete=models.SET_NULL, blank=True, null=True, related_name='played_songs')
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