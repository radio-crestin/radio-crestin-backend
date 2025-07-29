import json
import logging
import os
import shutil
import tempfile
import zipfile
from collections import defaultdict
from pathlib import Path

from celery import shared_task
from django.apps import apps
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.db import transaction, DEFAULT_DB_ALIAS
from django.db.models import ForeignKey
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


def extract_backup_archive(archive_path, extract_dir):
    """
    Extract a backup ZIP archive and return the path to the JSON file.

    Args:
        archive_path: Path to the ZIP archive
        extract_dir: Directory to extract files to

    Returns:
        Path to the extracted JSON backup file
    """
    with zipfile.ZipFile(archive_path, 'r') as zipf:
        # Extract all files
        zipf.extractall(extract_dir)
        logger.info(f"Extracted backup archive to {extract_dir}")

    # Return path to the standardized JSON file
    json_file_path = Path(extract_dir) / "backup.json"
    if not json_file_path.exists():
        raise FileNotFoundError(f"backup.json not found in archive at {json_file_path}")

    return str(json_file_path)


def restore_media_files_after_loaddata(extract_dir, backup_data):
    """
    Restore media files from extracted archive and update file fields in the database.
    This should be called AFTER loaddata commands to ensure proper field updates.

    Args:
        extract_dir: Directory where archive was extracted
        backup_data: Parsed JSON backup data to identify file fields

    Returns:
        Dict with 'restored' and 'failed' file lists
    """
    restored_files = []
    failed_files = []

    media_dir = Path(extract_dir) / 'media'
    if not media_dir.exists():
        logger.info("No media directory found in backup archive")
        return {'restored': [], 'failed': [],}

    # First, restore all media files to storage
    logger.info("Restoring media files to storage...")
    for file_path in media_dir.rglob('*'):
        if file_path.is_file():
            # Calculate relative path from media directory
            relative_path = file_path.relative_to(media_dir)
            storage_path = str(relative_path).replace('\\', '/')  # Ensure forward slashes

            try:
                # Read the file content
                with open(file_path, 'rb') as f:
                    file_content = f.read()

                # Save to Django storage (handles local, S3, etc.)
                if default_storage.exists(storage_path):
                    # Delete existing file first
                    default_storage.delete(storage_path)

                default_storage.save(storage_path, ContentFile(file_content))
                restored_files.append(storage_path)
                logger.debug(f"Restored media file: {storage_path}")

            except Exception as e:
                failed_files.append(storage_path)
                logger.error(f"Failed to restore media file {storage_path}: {e}")

    # Second, update file fields in database objects
    logger.info("Updating file fields in database objects...")
    file_field_references = _extract_file_field_references(backup_data)

    logger.info(f"Restored {len(restored_files)} media files, {len(failed_files)} failed")
    return {
        'restored': restored_files,
        'failed': failed_files,
    }


def _extract_file_field_references(backup_data):
    """
    Extract file field references from backup data.

    Args:
        backup_data: Parsed JSON backup data

    Returns:
        Dict mapping model_name -> {pk: {field_name: file_path}}
    """
    file_field_references = defaultdict(lambda: defaultdict(dict))

    for obj_data in backup_data:
        model_name = obj_data['model']
        pk = obj_data['pk']
        fields = obj_data['fields']

        try:
            app_label, model_class_name = model_name.split('.')
            model_class = apps.get_model(app_label, model_class_name)

            # Check each field to see if it's a file field
            for field_name, field_value in fields.items():
                try:
                    field = model_class._meta.get_field(field_name)
                    # Check if it's a FileField or ImageField
                    if hasattr(field, 'upload_to') and field_value:
                        file_field_references[model_name][pk][field_name] = field_value
                        logger.debug(f"Found file field: {model_name}[{pk}].{field_name} = {field_value}")
                except Exception:
                    # Field doesn't exist or isn't a file field, skip
                    continue

        except (ValueError, LookupError):
            # Model doesn't exist, skip
            continue

    return file_field_references


def determine_backup_type(file_path):
    """
    Determine if the backup file is a ZIP archive or JSON file.

    Args:
        file_path: Path to the backup file

    Returns:
        'zip' or 'json'
    """
    file_path_lower = file_path.lower()
    if file_path_lower.endswith('.zip'):
        return 'zip'
    elif file_path_lower.endswith('.json'):
        return 'json'
    else:
        # Try to determine by content
        try:
            with open(file_path, 'rb') as f:
                header = f.read(4)
                if header.startswith(b'PK'):  # ZIP file signature
                    return 'zip'
                else:
                    return 'json'
        except Exception:
            return 'json'  # Default to JSON


def _cleanup_existing_data_for_non_tenant_restore(file_path, exclude_models=None, using=DEFAULT_DB_ALIAS):
    """
    Clean up existing data before performing a non-tenant restore.

    This function:
    1. Parses the fixture file to identify which models will be loaded
    2. Deletes all existing data for those models (excluding excluded models)
    3. Handles foreign key constraints properly by deleting in dependency order

    Args:
        file_path: Path to the fixture JSON file
        exclude_models: List of model names to exclude from cleanup (format: 'app_label.model_name')
        using: Database alias to use
    """
    if exclude_models is None:
        exclude_models = []

    logger.info(f"Starting cleanup of existing data for non-tenant restore from {file_path}")

    try:
        # Parse the fixture file to get the models that will be loaded
        with open(file_path, 'r') as f:
            fixture_data = json.load(f)

        # Get unique model names from the fixture
        models_in_fixture = set()
        for obj in fixture_data:
            model_name = obj['model'].lower()
            models_in_fixture.add(model_name)

        logger.info(f"Found {len(models_in_fixture)} unique models in fixture: {models_in_fixture}")

        # Filter out excluded models
        models_to_cleanup = []
        for model_name in models_in_fixture:
            if model_name.lower() not in [ex.lower() for ex in exclude_models]:
                try:
                    app_label, model_class_name = model_name.split('.')
                    model_class = apps.get_model(app_label, model_class_name)
                    models_to_cleanup.append((model_name, model_class))
                    logger.info(f"Will cleanup model: {model_name}")
                except (ValueError, LookupError) as e:
                    logger.warning(f"Could not load model {model_name}: {e}")
            else:
                logger.info(f"Excluding model from cleanup: {model_name}")

        if not models_to_cleanup:
            logger.info("No models to cleanup")
            return

        # Group models by their dependency level to handle foreign key constraints
        dependency_levels = _calculate_model_dependency_levels(models_to_cleanup, using)

        # Delete in reverse dependency order (most dependent first)
        with transaction.atomic(using=using):
            for level in sorted(dependency_levels.keys(), reverse=True):
                level_models = dependency_levels[level]
                for model_name, model_class in level_models:
                    logger.info(f"Deleting all data from {model_name}")
                    deleted_count, _ = model_class.objects.using(using).all().delete()
                    logger.info(f"Deleted {deleted_count} records from {model_name}")

        logger.info("Successfully completed cleanup of existing data")

    except Exception as e:
        logger.error(f"Error during cleanup of existing data: {e}")
        raise


def _calculate_model_dependency_levels(models_to_cleanup, using=DEFAULT_DB_ALIAS):
    """
    Calculate dependency levels for models to determine deletion order.
    Models with higher levels depend on models with lower levels.

    Returns:
        dict: {level: [(model_name, model_class), ...]}
    """
    model_map = {model_name: model_class for model_name, model_class in models_to_cleanup}
    dependency_levels = defaultdict(list)
    model_levels = {}

    def get_model_level(model_name, model_class, visited=None):
        if visited is None:
            visited = set()

        if model_name in visited:
            # Circular dependency detected, assign a high level
            return 100

        if model_name in model_levels:
            return model_levels[model_name]

        visited.add(model_name)
        max_dependency_level = 0

        # Check all foreign key fields
        for field in model_class._meta.fields:
            if isinstance(field, ForeignKey):
                related_model = field.related_model
                related_model_name = f"{related_model._meta.app_label}.{related_model._meta.model_name}".lower()

                # Only consider dependencies on models that are also being cleaned up
                if related_model_name in model_map:
                    dependency_level = get_model_level(related_model_name, related_model, visited.copy())
                    max_dependency_level = max(max_dependency_level, dependency_level + 1)

        visited.remove(model_name)
        model_levels[model_name] = max_dependency_level
        return max_dependency_level

    # Calculate levels for all models
    for model_name, model_class in models_to_cleanup:
        level = get_model_level(model_name, model_class)
        dependency_levels[level].append((model_name, model_class))

    logger.info(f"Calculated dependency levels: {dict(dependency_levels)}")
    return dependency_levels


@shared_task(
    bind=True,
    name="backups.process_restore",
    max_retries=0,
    default_retry_delay=60,
    queue='priority',
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

        if MULTI_TENANT_ENABLED:
            restore = Restore.all_objects.get(pk=restore_pk)
        else:
            restore = Restore.objects.get(pk=restore_pk)
        tenant = restore.tenant if MULTI_TENANT_ENABLED else None
        logger.info(f"Processing restore with ID: {restore_pk} for tenant: {tenant}")

        # Set tenant context if we have a tenant
        if tenant:
            set_current_tenant(tenant)

        restore.started_at = timezone.now()
        restore.save(update_fields=['started_at'])

        # Determine which file to use: backup file or uploaded file
        temp_dir = None
        json_file_path = None
        media_restore_result = None
        backup_data = None
        has_media_files = False

        try:
            # First, copy the source file to a temporary location
            source_file = restore.file
            original_name = source_file.name
            logger.info(f"Processing backup file: {original_name}")

            # Create a temporary file with appropriate suffix based on source file
            file_extension = '.zip' if original_name.lower().endswith('.zip') else '.json'
            with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_file:
                temp_source_path = temp_file.name

                with source_file.open('rb') as src:
                    # Copy file content in chunks to avoid memory issues
                    for chunk in src.chunks():
                        temp_file.write(chunk)

                # Ensure data is written to disk before returning
                temp_file.flush()

            # Determine backup type and handle accordingly
            backup_type = determine_backup_type(temp_source_path)
            logger.info(f"Detected backup type: {backup_type}")

            if backup_type == 'zip':
                # Handle ZIP archive with media files
                temp_dir = tempfile.mkdtemp(prefix='restore_')
                logger.info(f"Created temporary directory for extraction: {temp_dir}")

                # Extract the archive and get JSON file path
                json_file_path = extract_backup_archive(temp_source_path, temp_dir)
                logger.info(f"Extracted JSON file to: {json_file_path}")

                # Check if media directory exists
                media_dir = Path(temp_dir) / 'media'
                has_media_files = media_dir.exists() and any(media_dir.rglob('*'))
                logger.info(f"Archive contains media files: {has_media_files}")

            else:
                # Handle direct JSON file
                json_file_path = temp_source_path
                logger.info(f"Using JSON file directly: {json_file_path}")

            # Parse backup data for later use in media restoration
            if has_media_files:
                logger.info("Parsing backup data for media file restoration...")
                with open(json_file_path, 'r') as f:
                    backup_data = json.load(f)

            # Clean up the temporary source file if we extracted it
            if backup_type == 'zip':
                try:
                    os.unlink(temp_source_path)
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary source file: {e}")

            # Set up options for the loaddata command
            options = {
                'database': 'default',
                'exclude':  settings.BACKUPS.get('BACKUP_TYPES', {}).get(restore.type, {}).get('exclude_models_from_import', []),
            }

            # If we have a tenant, use tenant_loaddata
            if MULTI_TENANT_ENABLED and tenant:
                options['no_cleanup'] = not restore.cleanup_existing_data
                options['tenant_pk'] = tenant.pk
                logger.info(f"Running tenant_loaddata for tenant {tenant.pk}")
                call_command('tenant_loaddata', json_file_path, **options)
            else:
                logger.info("Running loaddata (no tenant)")
                if restore.cleanup_existing_data:
                    logger.info("Cleanup existing data is enabled, cleaning up existing data from fixture models")
                    _cleanup_existing_data_for_non_tenant_restore(
                        file_path=json_file_path,
                        exclude_models=options.get('exclude', []),
                        using=options.get('database', 'default')
                    )

                call_command('loaddata', json_file_path, **options)

            # Now restore media files AFTER loaddata commands are complete
            if has_media_files and backup_data:
                logger.info("Starting media file restoration after successful data load...")
                media_restore_result = restore_media_files_after_loaddata(temp_dir, backup_data)
                logger.info(f"Media restoration completed: {len(media_restore_result['restored'])} files restored, "
                           f"{len(media_restore_result['failed'])} failed")
            else:
                logger.info("No media files to restore")

            # Clean up tenant context
            unset_current_tenant()

            # Set restore completion info
            restore.finished_at = timezone.now()
            restore.tenant = tenant
            restore.done = True

            restore.save(force_update=True)

            return restore.id

        finally:
            # Clean up temporary files and directories
            if json_file_path and os.path.exists(json_file_path):
                try:
                    os.unlink(json_file_path)
                    logger.debug(f"Cleaned up temporary JSON file: {json_file_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary JSON file: {e}")

            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    logger.debug(f"Cleaned up temporary directory: {temp_dir}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary directory: {e}")
    except Exception as exc:
        logger.exception(f"Error during restore process: {exc}")
        self.retry(exc=exc)
        return None
