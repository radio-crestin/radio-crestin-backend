from django.db import models
from django.utils.translation import gettext_lazy as _
from .stations import Stations


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