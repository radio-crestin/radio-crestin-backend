from django.db import models
from django.utils.translation import gettext_lazy as _


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