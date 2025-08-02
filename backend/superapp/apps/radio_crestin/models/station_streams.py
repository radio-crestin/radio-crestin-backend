from django.db import models
from django.utils.translation import gettext_lazy as _


class StationStreams(models.Model):
    STREAM_TYPES = [
        ('HLS', _('HLS')),
        ('proxied_stream', _('Proxied Stream')),
        ('direct_stream', _('Direct Stream')),
    ]

    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    station = models.ForeignKey('Stations', verbose_name=_("Station"), on_delete=models.CASCADE, related_name='station_streams')
    stream_url = models.TextField(_("Stream URL"))
    order = models.IntegerField(_("Order"), default=0)
    station_stream_order = models.FloatField(_("Station Stream Order"), blank=True, null=True, default=0)
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

    def save(self, *args, **kwargs):
        self.order = round(self.station_stream_order) if self.station_stream_order is not None else 0
        super().save(*args, **kwargs)