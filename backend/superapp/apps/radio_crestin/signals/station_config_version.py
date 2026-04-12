import logging

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from superapp.apps.radio_crestin.models import Stations, StationsMetadataFetch

logger = logging.getLogger(__name__)


@receiver(post_save, sender=StationsMetadataFetch)
def increment_config_version_on_fetcher_change(sender, instance, **kwargs):
    """When a scraper config changes, bump the station's config_version so the pod reloads."""
    Stations.objects.filter(id=instance.station_id).update(
        config_version=models.F('config_version') + 1
    )
    logger.info(f"Incremented config_version for station {instance.station_id} (fetcher change)")


@receiver(post_save, sender=Stations)
def increment_config_version_on_station_change(sender, instance, **kwargs):
    """When station streaming config fields change, bump config_version.
    Avoids infinite loop by checking update_fields when available."""
    update_fields = kwargs.get('update_fields')
    # Skip if this save is only updating the denormalized FK or config_version itself
    skip_fields = {'latest_station_now_playing', 'latest_station_uptime', 'config_version'}
    if update_fields and not (set(update_fields) - skip_fields):
        return

    config_fields = {
        'metadata_timestamp_source', 'metadata_scrape_interval',
        'id3_metadata_delay_offset', 'stream_url', 'transcode_enabled',
    }
    if update_fields and not (set(update_fields) & config_fields):
        return

    # Only bump if this is an update (not initial create) and not already handled
    if not kwargs.get('created', False) and update_fields is None:
        Stations.objects.filter(id=instance.id).update(
            config_version=models.F('config_version') + 1
        )
        logger.info(f"Incremented config_version for station {instance.id} (station config change)")
