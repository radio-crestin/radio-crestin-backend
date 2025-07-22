import logging
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.conf import settings

from superapp.apps.backups.models.backup import Backup
from superapp.apps.backups.tasks.backup import (
    get_models_for_backup_type,
    extract_media_files_from_fixture,
    copy_media_files_to_backup,
    create_backup_archive
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
    help = 'Create a backup synchronously with specified file path and backup type'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            required=True,
            help='File path where the backup will be saved'
        )
        parser.add_argument(
            '--backup-type',
            type=str,
            required=True,
            help='Type of backup to create (must be defined in BACKUPS.BACKUP_TYPES settings)'
        )
        parser.add_argument(
            '--name',
            type=str,
            help='Optional name for the backup (will be auto-generated if not provided)'
        )
        parser.add_argument(
            '--tenant-id',
            type=int,
            help='Tenant ID for multi-tenant backups (if multi-tenant is enabled)'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        backup_type = options['backup_type']
        backup_name = options.get('name')
        tenant_id = options.get('tenant_id')

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

            # Generate backup name if not provided
            if not backup_name:
                timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
                if tenant:
                    backup_name = f'Manual Backup - Tenant {tenant.pk} - {backup_type} - {timestamp}'
                else:
                    backup_name = f'Manual Backup - {backup_type} - {timestamp}'

            self.stdout.write(f'Creating backup: {backup_name}')
            self.stdout.write(f'Backup type: {backup_type}')
            self.stdout.write(f'File path: {file_path}')

            # Create backup record
            backup = Backup.objects.create(
                name=backup_name,
                type=backup_type
            )

            backup.started_at = timezone.now()
            backup.save(update_fields=['started_at'])

            # Use the synchronous backup creation logic
            self._create_backup_synchronously(backup, file_path)

            # Mark as completed
            backup.finished_at = timezone.now()
            backup.done = True
            backup.save(update_fields=['finished_at', 'done'])

            self.stdout.write(
                self.style.SUCCESS(f'Backup created successfully: {backup_name}')
            )
            self.stdout.write(f'Backup ID: {backup.id}')
            self.stdout.write(f'File saved to: {file_path}')

        except Exception as e:
            logger.error(f'Error creating backup: {e}')
            raise CommandError(f'Failed to create backup: {str(e)}')

        finally:
            # Clean up tenant context
            if MULTI_TENANT_ENABLED:
                unset_current_tenant()

    def _create_backup_synchronously(self, backup, target_file_path):
        """
        Create backup synchronously using the same logic as the Celery task
        """
        import tempfile
        import os
        import json
        from pathlib import Path
        from django.core.files.base import File
        from django.core.management import call_command
        from django.apps import apps

        # Create target directory if it doesn't exist
        target_path = Path(target_file_path)
        target_dir = target_path.parent
        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)
            self.stdout.write(f'Created directory: {target_dir}')

        # Get models to backup based on backup type
        models_to_backup = get_models_for_backup_type(backup.type)

        # If models_to_backup is '*', backup all models
        if models_to_backup == '*':
            args = []
            for app_config in apps.get_app_configs():
                for model in app_config.get_models():
                    model_name = f"{model._meta.app_label}.{model._meta.model_name}"
                    args.append(model_name)
        else:
            args = models_to_backup

        self.stdout.write(f'Backing up models: {", ".join(args)}')

        # Create a temporary directory for the backup process
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file_path = os.path.join(temp_dir, 'backup.json')

            # Set up options for the dumpdata command
            options = {
                'output': temp_file_path,
                'format': 'json',
                'indent': 2,
                'database': 'default',
            }

            # If multi-tenant is enabled and we have a tenant, use tenant-specific commands
            tenant = getattr(backup, 'tenant', None) if MULTI_TENANT_ENABLED else None
            if MULTI_TENANT_ENABLED and tenant:
                options['tenant_pk'] = tenant.pk
                call_command('tenant_dumpdata', *args, **options)
            else:
                call_command('dumpdata', *args, **options)

            # Read the generated JSON file to extract media file references
            with open(temp_file_path, 'r') as f:
                fixture_data = json.load(f)

            # Extract media files referenced in the fixture
            media_files = extract_media_files_from_fixture(fixture_data)
            self.stdout.write(f'Found {len(media_files)} media files referenced in backup')

            # Copy media files to backup directory
            media_copy_result = copy_media_files_to_backup(media_files, temp_dir)
            self.stdout.write(f'Copied {len(media_copy_result["copied"])} media files, '
                            f'{len(media_copy_result["missing"])} files were missing')

            # Create archive name based on target file path
            target_path = Path(target_file_path)
            archive_name = target_path.stem

            # Create zip archive with JSON data and media files
            archive_path = create_backup_archive(temp_file_path, temp_dir, archive_name)

            # Copy the archive to the target location
            import shutil
            shutil.copy2(archive_path, target_file_path)

            # Also save to the backup model for record keeping
            with open(archive_path, 'rb') as archive_file:
                backup.file.save(
                    name=f'{archive_name}.zip',
                    content=File(archive_file),
                    save=True
                )

            # Log backup statistics
            self.stdout.write(f'Media files: {len(media_copy_result["copied"])} copied, '
                            f'{len(media_copy_result["missing"])} missing')
            if media_copy_result['missing']:
                self.stdout.write(
                    self.style.WARNING(f'Missing media files: {media_copy_result["missing"]}')
                )