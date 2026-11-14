"""Keeps what clients see in step with the admin.

- Every change drops the cached API responses (services/announcement_feed).
- A change that the website shows schedules a website rebuild (services/web_deploy),
  because the website renders the card into its HTML at build time.
"""
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_save
from django.dispatch import receiver

from ..models import Announcement, AnnouncementCategory, AnnouncementImage, AnnouncementSettings
from ..services import announcement_html, web_deploy, youtube_embeds
from ..services.announcement_feed import invalidate_cache


@receiver([post_save, post_delete], sender=Announcement)
@receiver([post_save, post_delete], sender=AnnouncementCategory)
@receiver([post_save, post_delete], sender=AnnouncementSettings)
@receiver([post_save, post_delete], sender=AnnouncementImage)
def invalidate_announcements_cache(sender, **kwargs):
    invalidate_cache()


@receiver(m2m_changed, sender=Announcement.stations.through)
def on_stations_change(sender, instance, action, **kwargs):
    if not action.startswith('post_'):
        return
    invalidate_cache()
    if isinstance(instance, Announcement) and web_deploy.is_web_visible(instance.status, instance.platforms):
        web_deploy.schedule()


@receiver(pre_save, sender=Announcement)
def store_embed_details(sender, instance, update_fields=None, **kwargs):
    """Title and thumbnail of each YouTube embed on the page (fetched once per id, then kept)."""
    if update_fields is not None and 'embed_details' not in update_fields:
        return  # a partial save that doesn't write them
    embeds = announcement_html.page_embeds(instance.page_markdown)
    instance.embed_details = youtube_embeds.details_for(embeds, instance.embed_details or {})


@receiver(pre_save, sender=Announcement)
def remember_web_visibility(sender, instance, **kwargs):
    """Whether the stored version showed on the website, so hiding it also rebuilds."""
    previous = Announcement.objects.filter(pk=instance.pk).values('status', 'platforms').first() if instance.pk else None
    instance._was_web_visible = bool(previous) and web_deploy.is_web_visible(previous['status'], previous['platforms'])


@receiver(post_save, sender=Announcement)
def rebuild_website_on_save(sender, instance, **kwargs):
    if getattr(instance, '_was_web_visible', False) or web_deploy.is_web_visible(instance.status, instance.platforms):
        web_deploy.schedule()


@receiver(post_delete, sender=Announcement)
def rebuild_website_on_delete(sender, instance, **kwargs):
    if web_deploy.is_web_visible(instance.status, instance.platforms):
        web_deploy.schedule()


@receiver([post_save, post_delete], sender=AnnouncementCategory)
@receiver([post_save, post_delete], sender=AnnouncementSettings)
def rebuild_website_on_look_change(sender, **kwargs):
    """Category names and colors, and the rotation, are part of the rendered card."""
    if any(web_deploy.is_web_visible(status, platforms)
           for status, platforms in Announcement.objects.values_list('status', 'platforms')):
        web_deploy.schedule()
