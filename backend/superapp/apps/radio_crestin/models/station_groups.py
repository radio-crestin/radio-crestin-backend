from django.db import models
from django.utils.translation import gettext_lazy as _


class StationGroups(models.Model):
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    slug = models.SlugField(_("Slug"))
    name = models.TextField(_("Name"), unique=True)
    station_group_order = models.FloatField(_("Station Group Order"), default=0)
    order = models.IntegerField(_("Order"), default=0) # Deprecated, use station_group_order instead

    class Meta:
        managed = True
        verbose_name = _("Station Group")
        verbose_name_plural = _("Station Groups")
        db_table = 'station_groups'
        ordering = ('station_group_order',)

    def __str__(self):
        return f"{self.name} (station_group_order: {self.station_group_order})"

    def save(self, *args, **kwargs):
        self.order = round(self.station_group_order)
        super().save(*args, **kwargs)
