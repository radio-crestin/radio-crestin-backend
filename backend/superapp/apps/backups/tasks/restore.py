import logging
import tempfile

from celery import shared_task
from django.conf import settings
from django.core.management import call_command
from django.utils import timezone

from superapp.apps.backups.models.restore import Restore

# Conditional imports for multi-tenant support
try:
    from django_multitenant.utils import unset_current_tenant
    from superapp.apps.multi_tenant.middleware import set_current_tenant
    MULTI_TENANT_ENABLED = True
except ImportError:
    MULTI_TENANT_ENABLED = False
    
    def unset_current_tenant():
        pass
    
    def set_current_tenant(tenant):
        pass

logger = logging.getLogger(__name__)

@shared_task(
    bind=True,
    name="backups.process_restore",
    max_retries=3,
    default_retry_delay=60,
)
def process_restore(self, restore_pk):
    """
    Celery task to restore data from a backup file for a tenant.

    Args:
        restore_pk: The primary key of the Restore object to be processed

    Returns:
        The ID of the processed restore
    """
    try:
        # Clear any existing tenant first
        unset_current_tenant()

        restore = Restore.objects.get(pk=restore_pk)
        tenant = getattr(restore, 'tenant', None) if MULTI_TENANT_ENABLED else None
        logger.info(f"Processing restore with ID: {restore_pk} for tenant: {tenant}")

        restore.started_at = timezone.now()
        restore.save(update_fields=['started_at'])

        # Determine which file to use: backup file or uploaded file
        file_path = None
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp_file:
            file_path = temp_file.name

            source_file = restore.file
            logger.info(f"Copying file to: {file_path}")

            with source_file.open('rb') as src:
                # Copy file content in chunks to avoid memory issues
                for chunk in src.chunks():
                    temp_file.write(chunk)

            # Ensure data is written to disk before returning
            temp_file.flush()

        # Set up options for the loaddata command
        options = {
            'database': 'default',
            'exclude':  settings.BACKUPS.get('BACKUP_TYPES', {}).get(restore.type, {}).get('exclude_models_from_import', []),
        }

        # If we have multi-tenant enabled and a tenant, use tenant_loaddata
        if MULTI_TENANT_ENABLED and tenant:
            options['no_cleanup'] = not restore.cleanup_existing_data
            options['tenant_pk'] = tenant.pk
            logger.info(f"Running tenant_loaddata for tenant {tenant.pk}")
            call_command('tenant_loaddata', file_path, **options)
        else:
            logger.info("Running loaddata (no tenant)")
            call_command('loaddata', file_path, **options)

        restore.finished_at = timezone.now()
        restore.done = True
        restore.save(update_fields=['done', 'finished_at'])

        # Clean up tenant context
        unset_current_tenant()

        return restore.id
    except Exception as exc:
        logger.exception(f"Error during restore process: {exc}")
        self.retry(exc=exc)
        return None
