import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from superapp.apps.radio_crestin.models import Stations, StationsMetadataFetch, StationMetadataFetchCategories

logger = logging.getLogger(__name__)

STREAM_ID3_SLUG = 'stream_id3'
DEFAULT_ID3_PRIORITY = 0  # Lowest priority — admin-configured scrapers override


@receiver(post_save, sender=Stations)
def auto_create_stream_id3_fetcher(sender, instance, created, **kwargs):
    """
    Auto-create a stream_id3 metadata fetcher for new stations.

    Also updates the URL if the station's stream_url changes and the
    existing ID3 fetcher still points to the old URL.

    Uses priority=0 so any manually configured scrapers (priority >= 1)
    take precedence during metadata merging.
    """
    if not instance.stream_url:
        return

    try:
        category = StationMetadataFetchCategories.objects.get(slug=STREAM_ID3_SLUG)
    except StationMetadataFetchCategories.DoesNotExist:
        logger.warning(f"StationMetadataFetchCategories '{STREAM_ID3_SLUG}' not found — skipping auto-create")
        return

    if created:
        # New station: create the default ID3 fetcher
        StationsMetadataFetch.objects.create(
            station=instance,
            station_metadata_fetch_category=category,
            url=instance.stream_url,
            priority=DEFAULT_ID3_PRIORITY,
            dirty_metadata=True,
        )
        logger.info(f"Auto-created stream_id3 fetcher for new station '{instance.slug}'")
    else:
        # Existing station: update the auto-created ID3 fetcher's URL if stream_url changed
        update_fields = kwargs.get('update_fields')
        if update_fields and 'stream_url' not in update_fields:
            return

        auto_fetcher = StationsMetadataFetch.objects.filter(
            station=instance,
            station_metadata_fetch_category=category,
            priority=DEFAULT_ID3_PRIORITY,
        ).first()

        if auto_fetcher and auto_fetcher.url != instance.stream_url:
            auto_fetcher.url = instance.stream_url
            auto_fetcher.save(update_fields=['url', 'updated_at'])
            logger.info(f"Updated stream_id3 fetcher URL for station '{instance.slug}'")
