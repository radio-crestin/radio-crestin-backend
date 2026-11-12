"""Drops the cached announcement responses whenever something they serve changes in the admin."""
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from ..models import Announcement, AnnouncementCategory, AnnouncementImage, AnnouncementSettings
from ..services.announcement_feed import invalidate_cache


@receiver([post_save, post_delete], sender=Announcement)
@receiver([post_save, post_delete], sender=AnnouncementCategory)
@receiver([post_save, post_delete], sender=AnnouncementSettings)
@receiver([post_save, post_delete], sender=AnnouncementImage)
def invalidate_announcements_cache(sender, **kwargs):
    invalidate_cache()


@receiver(m2m_changed, sender=Announcement.stations.through)
def on_stations_change(sender, action, **kwargs):
    if action.startswith('post_'):
        invalidate_cache()
