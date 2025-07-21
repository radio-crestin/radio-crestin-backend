import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from superapp.apps.backups.models.restore import Restore
from superapp.apps.backups.tasks.restore import process_restore

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Restore)
def restore_post_save(sender, instance, created, raw, **kwargs):
    """
    Signal handler for Restore model post-save.
    If a new restore is created, dispatch the task to process it.
    """
    if raw:
        return
    if created:
        logger.info(f"New restore created with ID: {instance.pk}")
        # Dispatch the restore task
        process_restore.delay(instance.pk)
