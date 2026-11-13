from django.db import models
from django.utils.translation import gettext_lazy as _

from .announcements import Announcement


class StatGranularity(models.TextChoices):
    HOUR = 'hour', _('Hour')
    DAY = 'day', _('Day')


class AnnouncementStatBucket(models.Model):
    """One announcement's events in one hour or one day, rolled up from the raw events.

    Hours start on the UTC hour; days are calendar days in Bucharest, stored as the UTC
    instant of their local midnight. Each row holds absolute counts, recomputed from the
    events (services/announcement_stat_buckets.py), so it outlives the 180-day event retention.
    """

    # No index of its own: the unique constraint below starts with it.
    announcement = models.ForeignKey(
        Announcement, on_delete=models.CASCADE, related_name='stat_buckets', db_index=False)
    granularity = models.CharField(_("Granularity"), max_length=8, choices=StatGranularity.choices)
    bucket_start = models.DateTimeField(_("Starts at"))
    impressions = models.PositiveIntegerField(_("Impressions"), default=0)
    clicks = models.PositiveIntegerField(_("Clicks"), default=0)
    secondary_clicks = models.PositiveIntegerField(_("Second button clicks"), default=0)
    dismissals = models.PositiveIntegerField(_("Closes"), default=0)
    page_views = models.PositiveIntegerField(_("Page views"), default=0)
    push_opens = models.PositiveIntegerField(_("Notification opens"), default=0)
    video_plays = models.PositiveIntegerField(_("Video plays"), default=0)
    unique_viewers = models.PositiveIntegerField(_("Unique viewers"), default=0)
    unique_clickers = models.PositiveIntegerField(_("Unique clickers"), default=0)

    class Meta:
        managed = True
        db_table = 'announcement_stat_buckets'
        ordering = ('announcement', 'granularity', 'bucket_start')
        verbose_name = _("Announcement Stat Bucket")
        verbose_name_plural = _("Announcement Stat Buckets")
        constraints = [
            # Also the index for reading one announcement's range of hours or days.
            models.UniqueConstraint(fields=['announcement', 'granularity', 'bucket_start'],
                                    name='announcement_stat_bucket_unique'),
        ]

    def __str__(self):
        return f"{self.announcement_id} · {self.granularity} · {self.bucket_start:%Y-%m-%d %H:%M}"
