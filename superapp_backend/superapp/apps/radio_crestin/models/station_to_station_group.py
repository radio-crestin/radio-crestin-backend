from django.db import models
from django.utils.translation import gettext_lazy as _
from .station_groups import StationGroups


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