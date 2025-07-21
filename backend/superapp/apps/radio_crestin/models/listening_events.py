from django.db import models
from django.utils.translation import gettext_lazy as _


class ListeningEvents(models.Model):
    """
    Model to track user listening events for analytics.
    """
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    user = models.ForeignKey(
        'radio_crestin.AppUsers',
        verbose_name=_("App Users"),
        on_delete=models.CASCADE,
        related_name='listening_events'
    )

    station = models.ForeignKey(
        'Stations',
        verbose_name=_("Station"),
        on_delete=models.CASCADE,
        related_name='listening_events'
    )

    session_id = models.TextField(_("Session ID"), blank=True, null=True)
    duration_seconds = models.IntegerField(_("Duration in seconds"), default=0)
    start_time = models.DateTimeField(_("Start time"))
    end_time = models.DateTimeField(_("End time"), blank=True, null=True)
    ip_address = models.GenericIPAddressField(_("IP Address"), blank=True, null=True)
    user_agent = models.TextField(_("User Agent"), blank=True, null=True)
    info = models.JSONField(_("Info"), blank=True, null=True)

    class Meta:
        managed = True
        verbose_name = _("Listening Event")
        verbose_name_plural = _("Listening Events")
        db_table = 'listening_events'
        ordering = ('-created_at',)

    def __str__(self):
        return f"{self.user.username} - {self.station.title} - {self.start_time}"
