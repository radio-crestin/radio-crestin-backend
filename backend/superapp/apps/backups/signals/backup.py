import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from superapp.apps.backups.models.backup import Backup
from superapp.apps.backups.tasks.backup import process_backup

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Backup)
def backup_post_save(sender, instance, created, raw, **kwargs):
    """
    Signal handler for Backup model post-save.
    """
    if raw:
        return
    if created:
        logger.info(f"New backup created with ID: {instance.pk}")
        # Dispatch the restore task
        process_backup.delay(instance.pk)
