from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator


class Reviews(models.Model):
    """
    Model for user reviews of radio stations.
    Reviews are unique per IP address and station - if same IP submits another review
    for the same station, the existing review is updated.
    """
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    user = models.ForeignKey(
        'radio_crestin.AppUsers',
        verbose_name=_("App User"),
        on_delete=models.SET_NULL,
        related_name='radio_reviews',
        blank=True,
        null=True
    )

    station = models.ForeignKey(
        'Stations',
        verbose_name=_("Station"),
        on_delete=models.CASCADE,
        related_name='reviews'
    )

    ip_address = models.GenericIPAddressField(
        _("IP Address"),
        help_text=_("IP address of the reviewer"),
        default='0.0.0.0'  # Default for migration, will be overwritten on upsert
    )

    user_identifier = models.CharField(
        _("User Identifier"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Unique identifier sent by the client (e.g., device ID, anonymous ID)")
    )

    stars = models.IntegerField(
        _("Stars"),
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )

    message = models.TextField(_("Message"), blank=True, null=True)
    verified = models.BooleanField(_("Verified"), default=True)

    class Meta:
        managed = True
        verbose_name = _("Review")
        verbose_name_plural = _("Reviews")
        db_table = 'reviews'
        ordering = ('-created_at',)
        unique_together = [['station', 'ip_address']]
        indexes = [
            models.Index(fields=['station', 'ip_address']),
            models.Index(fields=['user_identifier']),
        ]

    def __str__(self):
        station_title = self.station.title if self.station else "Unknown"
        return f"{self.ip_address} - {station_title} - {self.stars} stars"
