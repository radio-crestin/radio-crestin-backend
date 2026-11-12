from django.db import models
from django.utils.translation import gettext_lazy as _

from .announcements import Announcement


class AnnouncementEventType(models.TextChoices):
    IMPRESSION = 'impression', _('Impression')
    CLICKED = 'clicked', _('Clicked')
    SECONDARY_CLICKED = 'secondary_clicked', _('Second button clicked')
    DISMISSED = 'dismissed', _('Closed')
    PAGE_VIEWED = 'page_viewed', _('Page viewed')
    PUSH_OPENED = 'push_opened', _('Notification opened')
    VIDEO_PLAY = 'video_play', _('Video played')


class AnnouncementEventTarget(models.TextChoices):
    CARD = 'card', _('Card')
    BUTTON = 'button', _('Button')


# Event type -> the Announcement counter it increments.
COUNTER_FIELD_BY_EVENT_TYPE = {
    AnnouncementEventType.IMPRESSION: 'impressions',
    AnnouncementEventType.CLICKED: 'clicks',
    AnnouncementEventType.SECONDARY_CLICKED: 'secondary_clicks',
    AnnouncementEventType.DISMISSED: 'dismissals',
    AnnouncementEventType.PAGE_VIEWED: 'page_views',
    AnnouncementEventType.PUSH_OPENED: 'push_opens',
    AnnouncementEventType.VIDEO_PLAY: 'video_plays',
}


class AnnouncementEvent(models.Model):
    """One raw event reported by a client. Deleted after 180 days; totals stay on the announcement."""

    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='events')
    type = models.CharField(_("Type"), max_length=32, choices=AnnouncementEventType.choices)
    device_id = models.CharField(_("Device ID"), max_length=512, blank=True, default='')
    platform = models.CharField(_("Platform"), max_length=32, blank=True, default='')
    app_version = models.CharField(_("App version"), max_length=64, blank=True, default='')
    locale = models.CharField(_("Locale"), max_length=64, blank=True, default='')
    country = models.CharField(_("Country"), max_length=2, blank=True, default='')
    ip = models.GenericIPAddressField(_("IP address"), null=True, blank=True)
    position = models.SmallIntegerField(_("Position"), null=True, blank=True)
    placement = models.CharField(_("Placement"), max_length=16, blank=True, default='')
    station_slug = models.CharField(_("Station"), max_length=100, blank=True, default='')
    target = models.CharField(
        _("Tapped"), max_length=16, choices=AnnouncementEventTarget.choices, blank=True, default='',
        help_text=_("For clicks: the whole card or the button."),
    )
    detail = models.CharField(
        _("Detail"), max_length=32, blank=True, default='', help_text=_("For video plays: provider:kind."),
    )
    occurred_at = models.DateTimeField(_("Occurred at (client)"), null=True, blank=True)
    created_at = models.DateTimeField(_("Received at"), auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'announcement_events'
        ordering = ('-created_at',)
        verbose_name = _("Announcement Event")
        verbose_name_plural = _("Announcement Events")
        indexes = [
            models.Index(fields=['announcement', 'created_at'], name='announcement_event_ann_idx'),
            models.Index(fields=['created_at'], name='announcement_event_time_idx'),
        ]
        constraints = [
            # A device's close counts once per announcement (the events endpoint relies on it).
            models.UniqueConstraint(
                fields=['announcement', 'device_id'], condition=models.Q(type='dismissed'),
                name='announcement_event_one_dismissal',
            ),
        ]

    def __str__(self):
        return f"{self.type} · {self.announcement_id} · {self.device_id}"
