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
    name="backups.automated_weekly_backup",
    max_retries=3,
    default_retry_delay=60,
)
def automated_weekly_backup(self):
    """
    Automated weekly backup task for essential data.
    
    Creates a backup of essential data and triggers cleanup of old backups.
    """
    try:
        logger.info("Starting automated weekly backup of essential data")
        
        # Create backup instance
        backup = Backup.objects.create(
            name=f"Weekly Essential Data Backup {timezone.now().strftime('%Y-%m-%d')}",
            type='essential_data'
        )
        
        # Process the backup
        backup_id = process_backup.apply_async(args=[backup.pk]).get()
        
        if backup_id:
            logger.info(f"Weekly backup created successfully with ID: {backup_id}")
            
            # Trigger cleanup of old backups
            cleanup_old_backups.apply_async()
            
            return backup_id
        else:
            logger.error("Failed to create weekly backup")
            return None
            
    except Exception as exc:
        logger.error(f"Error in automated weekly backup: {exc}")
        self.retry(exc=exc)
        return None


@shared_task(
    bind=True,
    name="backups.cleanup_old_backups",
    max_retries=3,
    default_retry_delay=60,
)
def cleanup_old_backups(self, backup_type='essential_data'):
    """
    Cleanup old backups to maintain retention limit.
    
    Args:
        backup_type: The type of backups to cleanup (default: 'essential_data')
    """
    try:
        max_backups = getattr(settings, 'BACKUPS', {}).get('RETENTION', {}).get('MAX_BACKUPS', 10)
        
        logger.info(f"Cleaning up old backups for type: {backup_type}, keeping {max_backups} most recent")
        
        # Get all completed backups of the specified type, ordered by creation date (newest first)
        completed_backups = Backup.objects.filter(
            type=backup_type,
            done=True
        ).order_by('-created_at')
        
        # Count total backups
        total_backups = completed_backups.count()
        
        if total_backups > max_backups:
            # Get backups to delete (everything beyond the retention limit)
            backups_to_delete = completed_backups[max_backups:]
            delete_count = backups_to_delete.count()
            
            logger.info(f"Found {total_backups} backups, will delete {delete_count} old backups")
            
            # Delete old backup files and records
            for backup in backups_to_delete:
                if backup.file:
                    try:
                        backup.file.delete(save=False)
                        logger.info(f"Deleted backup file: {backup.file.name}")
                    except Exception as e:
                        logger.warning(f"Could not delete backup file {backup.file.name}: {e}")
                
                backup.delete()
                logger.info(f"Deleted backup record: {backup.name}")
            
            logger.info(f"Cleanup completed. Deleted {delete_count} old backups")
            return delete_count
        else:
            logger.info(f"No cleanup needed. Found {total_backups} backups, limit is {max_backups}")
            return 0
            
    except Exception as exc:
        logger.error(f"Error in backup cleanup: {exc}")
        self.retry(exc=exc)
        return None
