"""Drops the cached announcements list whenever something it serves changes in the admin."""
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from ..models import Announcement, AnnouncementCategory, AnnouncementSettings
from ..services.announcement_feed import invalidate_cache


@receiver([post_save, post_delete], sender=Announcement)
@receiver([post_save, post_delete], sender=AnnouncementCategory)
@receiver([post_save, post_delete], sender=AnnouncementSettings)
def invalidate_announcements_cache(sender, **kwargs):
    invalidate_cache()


@receiver(m2m_changed, sender=Announcement.target_devices.through)
def invalidate_announcements_cache_on_devices_change(sender, **kwargs):
    invalidate_cache()
