import logging
import os
import tempfile
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.conf import settings

from superapp.apps.backups.models.restore import Restore
from superapp.apps.backups.tasks.restore import (
    extract_backup_archive,
    restore_media_files_after_loaddata,
    determine_backup_type,
    _cleanup_existing_data_for_non_tenant_restore
)

# Conditional imports for multi-tenant support
try:
    from django_multitenant.utils import unset_current_tenant
    from superapp.apps.multi_tenant.middleware import set_current_tenant
    from superapp.apps.multi_tenant.models import Tenant
    MULTI_TENANT_ENABLED = True
except ImportError:
    MULTI_TENANT_ENABLED = False

    def unset_current_tenant():
        pass

    def set_current_tenant(tenant):
        pass

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Restore data synchronously from a backup file with specified backup type'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            required=True,
            help='Path to backup file to restore (can be .zip or .json)'
        )
        parser.add_argument(
            '--backup-type',
            type=str,
            required=True,
            help='Type of backup being restored (must be defined in BACKUPS.BACKUP_TYPES settings)'
        )
        parser.add_argument(
            '--name',
            type=str,
            help='Optional name for the restore operation (will be auto-generated if not provided)'
        )
        parser.add_argument(
            '--tenant-id',
            type=int,
            help='Tenant ID for multi-tenant restores (if multi-tenant is enabled)'
        )
        parser.add_argument(
            '--cleanup-existing-data',
            action='store_true',
            default=False,
            help='Clean up existing data before restoring (default: False)'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        backup_type = options['backup_type']
        restore_name = options.get('name')
        tenant_id = options.get('tenant_id')
        cleanup_existing_data = options['cleanup_existing_data']

        # Validate file path
        if not os.path.exists(file_path):
            raise CommandError(f'Backup file does not exist: {file_path}')

        # Validate backup type
        backup_types = getattr(settings, 'BACKUPS', {}).get('BACKUP_TYPES', {})
        if backup_type not in backup_types:
            available_types = ', '.join(backup_types.keys())
            raise CommandError(f'Invalid backup type "{backup_type}". Available types: {available_types}')

        # Handle multi-tenant setup if enabled
        tenant = None
        if MULTI_TENANT_ENABLED and tenant_id:
            try:
                tenant = Tenant.objects.get(pk=tenant_id)
                set_current_tenant(tenant)
                self.stdout.write(f'Set tenant context: {tenant}')
            except Tenant.DoesNotExist:
                raise CommandError(f'Tenant with ID {tenant_id} does not exist')

        try:
            # Clear any existing tenant first
            unset_current_tenant()
            if tenant:
                set_current_tenant(tenant)

            # Generate restore name if not provided
            if not restore_name:
                timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
                if tenant:
                    restore_name = f'Manual Restore - Tenant {tenant.pk} - {backup_type} - {timestamp}'
                else:
                    restore_name = f'Manual Restore - {backup_type} - {timestamp}'

            self.stdout.write(f'Starting restore: {restore_name}')
            self.stdout.write(f'Backup type: {backup_type}')
            self.stdout.write(f'Source file: {file_path}')
            self.stdout.write(f'Cleanup existing data: {cleanup_existing_data}')

            # Create restore record for tracking and upload the local file
            restore = Restore(
                name=restore_name,
                type=backup_type,
                cleanup_existing_data=cleanup_existing_data
            )
            
            # Upload the local backup file to the restore record
            with open(file_path, 'rb') as backup_file:
                from django.core.files.base import ContentFile
                file_name = os.path.basename(file_path)
                restore.file.save(file_name, ContentFile(backup_file.read()), save=False)
            
            restore.save()

            restore.started_at = timezone.now()
            restore.save(update_fields=['started_at'])

            # Perform the synchronous restore
            self._restore_backup_synchronously(restore, file_path, backup_type, cleanup_existing_data)

            # Mark as completed
            restore.finished_at = timezone.now()
            restore.done = True
            restore.save(update_fields=['finished_at', 'done'])

            self.stdout.write(
                self.style.SUCCESS(f'Restore completed successfully: {restore_name}')
            )
            self.stdout.write(f'Restore ID: {restore.id}')

        except Exception as e:
            logger.error(f'Error restoring backup: {e}')
            raise CommandError(f'Failed to restore backup: {str(e)}')

        finally:
            # Clean up tenant context
            if MULTI_TENANT_ENABLED:
                unset_current_tenant()

    def _restore_backup_synchronously(self, restore, source_file_path, backup_type, cleanup_existing_data):
        """
        Restore backup synchronously using the same logic as the Celery task
        """
        from django.core.management import call_command
        import shutil

        temp_dir = None
        json_file_path = None
        temp_source_path = None
        has_media_files = False
        backup_data = None

        try:
            # Determine backup file type
            backup_file_type = determine_backup_type(source_file_path)
            self.stdout.write(f'Detected backup file type: {backup_file_type}')

            if backup_file_type == 'zip':
                # Handle ZIP archive with media files
                temp_dir = tempfile.mkdtemp(prefix='restore_')
                self.stdout.write(f'Created temporary directory: {temp_dir}')

                # Extract the archive and get JSON file path
                json_file_path = extract_backup_archive(source_file_path, temp_dir)
                self.stdout.write(f'Extracted JSON file to: {json_file_path}')

                # Check if media directory exists
                media_dir = Path(temp_dir) / 'media'
                has_media_files = media_dir.exists() and any(media_dir.rglob('*'))
                self.stdout.write(f'Archive contains media files: {has_media_files}')

            else:
                # Handle direct JSON file - copy to temporary location for consistent handling
                temp_source_path = tempfile.mktemp(suffix='.json')
                shutil.copy2(source_file_path, temp_source_path)
                json_file_path = temp_source_path
                self.stdout.write(f'Using JSON file: {json_file_path}')

            # Parse backup data for later use in media restoration if needed
            if has_media_files:
                self.stdout.write('Parsing backup data for media file restoration...')
                with open(json_file_path, 'r') as f:
                    backup_data = json.load(f)

            # Set up options for the loaddata command
            backup_config = settings.BACKUPS.get('BACKUP_TYPES', {}).get(backup_type, {})
            exclude_models = backup_config.get('exclude_models_from_import', [])
            
            options = {
                'database': 'default',
                'exclude': exclude_models,
            }

            self.stdout.write(f'Exclude models: {exclude_models}')

            # Handle tenant-specific vs non-tenant restore
            if MULTI_TENANT_ENABLED and hasattr(restore, 'tenant') and restore.tenant:
                # Tenant-specific restore
                options['no_cleanup'] = not cleanup_existing_data
                options['tenant_pk'] = restore.tenant.pk
                self.stdout.write(f'Running tenant_loaddata for tenant {restore.tenant.pk}')
                call_command('tenant_loaddata', json_file_path, **options)
            else:
                # Non-tenant restore
                self.stdout.write('Running loaddata (no tenant)')
                if cleanup_existing_data:
                    self.stdout.write('Cleanup existing data is enabled, cleaning up existing data from fixture models')
                    _cleanup_existing_data_for_non_tenant_restore(
                        file_path=json_file_path,
                        exclude_models=exclude_models,
                        using=options.get('database', 'default')
                    )

                call_command('loaddata', json_file_path, **options)

            # Restore media files AFTER loaddata commands are complete
            if has_media_files and backup_data:
                self.stdout.write('Starting media file restoration after successful data load...')
                media_restore_result = restore_media_files_after_loaddata(temp_dir, backup_data)
                self.stdout.write(f'Media restoration completed: {len(media_restore_result["restored"])} files restored, '
                                f'{len(media_restore_result["failed"])} failed')
                
                if media_restore_result['failed']:
                    self.stdout.write(
                        self.style.WARNING(f'Failed to restore media files: {media_restore_result["failed"]}')
                    )
            else:
                self.stdout.write('No media files to restore')

        finally:
            # Clean up temporary files and directories
            if json_file_path and json_file_path != source_file_path and os.path.exists(json_file_path):
                try:
                    os.unlink(json_file_path)
                    self.stdout.write(f'Cleaned up temporary JSON file: {json_file_path}')
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Failed to clean up temporary JSON file: {e}'))

            if temp_source_path and os.path.exists(temp_source_path):
                try:
                    os.unlink(temp_source_path)
                    self.stdout.write(f'Cleaned up temporary source file: {temp_source_path}')
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Failed to clean up temporary source file: {e}'))

            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    self.stdout.write(f'Cleaned up temporary directory: {temp_dir}')
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Failed to clean up temporary directory: {e}'))