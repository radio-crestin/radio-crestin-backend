from django.db import models
from django.utils.translation import gettext_lazy as _


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