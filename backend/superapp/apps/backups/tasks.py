import logging
from celery import shared_task
import tempfile
import os
from django.conf import settings
from django.core.files.base import ContentFile, File
from django.core.management import call_command
from django.utils import timezone
from django.apps import apps

from superapp.apps.backups.models.backup import Backup
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

def get_models_for_backup_type(backup_type):
    """
    Get the list of models to backup based on the backup type.

    Args:
        backup_type: The backup type string

    Returns:
        List of model names to backup, or '*' for all models
    """
    # Get backup types from settings
    backup_types = getattr(settings, 'BACKUPS', {}).get('BACKUP_TYPES', {})

    # If the backup type doesn't exist in settings, default to all models
    if backup_type not in backup_types:
        return '*'

    # Get the models from the backup type configuration
    backup_type_config = backup_types.get(backup_type, {})
    return backup_type_config.get('models', '*')

@shared_task(
    bind=True,
    name="backups.process_backup",
    max_retries=3,
    default_retry_delay=60,
)
def process_backup(self, backup_pk):
    """
    Celery task to create a backup for a tenant.

    Args:
        backup_pk: The primary key of the Backup object to be processed

    Returns:
        The ID of the created backup
    """
    try:
        # Clear any existing tenant first
        unset_current_tenant()

        backup = Backup.objects.get(pk=backup_pk)
        tenant = getattr(backup, 'tenant', None) if MULTI_TENANT_ENABLED else None
        logger.info(f"Processing backup with ID: {backup_pk} for tenant: {tenant} of type: {backup.type}")

        # Set the tenant context
        if MULTI_TENANT_ENABLED and tenant:
            set_current_tenant(tenant)

        backup.started_at = timezone.now()
        backup.save(update_fields=['started_at'])

        # Get models to backup based on backup type
        models_to_backup = get_models_for_backup_type(backup.type)

        # If models_to_backup is '*', backup all models
        if models_to_backup == '*':
            # Get all installed models
            args = []
            for app_config in apps.get_app_configs():
                for model in app_config.get_models():
                    model_name = f"{model._meta.app_label}.{model._meta.model_name}"
                    args.append(model_name)
        else:
            # Use the specific models defined in the backup type
            args = models_to_backup

        print(args)
        with tempfile.NamedTemporaryFile(suffix='.json') as temp_file:
            temp_file_path = temp_file.name

            # Set up options for the dumpdata command
            options = {
                'output': temp_file_path,
                'format': 'json',
                'indent': 2,
                'database': 'default',
            }
            
            # If multi-tenant is enabled and we have a tenant, use tenant-specific commands
            if MULTI_TENANT_ENABLED and tenant:
                options['tenant_pk'] = tenant.pk
                call_command('tenant_dumpdata', *args, **options)
            else:
                call_command('dumpdata', *args, **options)

            temp_file.seek(0)

            backup.finished_at = timezone.now()
            if MULTI_TENANT_ENABLED and tenant:
                backup.file.save(
                    name=f'backup_{tenant.pk}_{backup.type}_{backup.finished_at.strftime("%Y%m%d_%H%M%S")}.json',
                    content=File(temp_file),
                    save=True
                )
            else:
                backup.file.save(
                    name=f'backup_{backup.type}_{backup.finished_at.strftime("%Y%m%d_%H%M%S")}.json',
                    content=File(temp_file),
                    save=True
                )
            backup.done = True
            backup.save(update_fields=['file', 'done', 'finished_at'])

        # Clean up tenant context
        unset_current_tenant()

        return backup.id
    except Exception as exc:
        self.retry(exc=exc)
        return None


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

        # Set the tenant context
        if MULTI_TENANT_ENABLED and tenant:
            set_current_tenant(tenant)

        restore.started_at = timezone.now()
        restore.save(update_fields=['started_at'])

        # Determine which file to use: backup file or uploaded file
        file_path = None
        if restore.backup and restore.backup.file:
            file_path = restore.backup.file.path
            logger.info(f"Using backup file: {file_path}")
        elif restore.file:
            file_path = restore.file.path
            logger.info(f"Using uploaded file: {file_path}")
        else:
            error_message = "No file available for restore operation."
            logger.error(error_message)
            raise ValueError(error_message)

        # Set up options for the loaddata command
        options = {
            'database': 'default',
            'ignorenonexistent': True,
        }

        # If we have multi-tenant enabled and a tenant, use tenant_loaddata
        if MULTI_TENANT_ENABLED and tenant:
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
