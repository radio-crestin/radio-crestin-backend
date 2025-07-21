from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator


class Reviews(models.Model):
    """
    Model for user reviews of radio stations.
    """
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    user = models.ForeignKey(
        'radio_crestin.AppUsers',
        verbose_name=_("App User"),
        on_delete=models.CASCADE,
        related_name='radio_reviews'
    )

    station = models.ForeignKey(
        'Stations',
        verbose_name=_("Station"),
        on_delete=models.CASCADE,
        related_name='reviews'
    )

    stars = models.IntegerField(
        _("Stars"),
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )

    message = models.TextField(_("Message"), blank=True, null=True)
    verified = models.BooleanField(_("Verified"), default=False)

    class Meta:
        managed = True
        verbose_name = _("Review")
        verbose_name_plural = _("Reviews")
        db_table = 'reviews'
        ordering = ('-created_at',)
        unique_together = [['station', 'user']]

    def __str__(self):
        return f"{self.user.username} - {self.station.title} - {self.stars} stars"
