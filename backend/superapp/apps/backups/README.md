# Django SuperApp - Sample App
### Getting Started
1. Setup the project using the instructions from https://django-superapp.bringes.io/
2. Setup `backups` app using the below instructions:
```bash
cd my_superapp;
cd superapp/apps;
django_superapp bootstrap-app \
    --template-repo https://github.com/django-superapp/django-superapp-backups ./backups;
cd ../../;
```
3. Configure the app in `settings.py`:
```python
from deepmerge import always_merger
from django.utils.translation import gettext_lazy as _


def extend_superapp_settings(main_settings):
    # Add tenant_models to the backup settings
    main_settings.update(
        always_merger.merge(
            {
                'BACKUPS': {
                    'BACKUP_TYPES': {
                        'common_models': {
                            'name': _('Common models'),
                            'description': _('Backup all common models'),
                            'models': [
                                "my_app.translation",
                                "my_app.translationvalues",
                                "my_app.location",
                                "auth.group",
                                "whatsapp.phonenumber",
                            ],
                            'exclude_models_from_import': [
                                "backups.backup",
                                "backups.restore",
                            ],
                        },
                        'organization': {
                            'name': _('Organization models'),
                            'description': _('Backup all organization models'),
                            'models': [
                                "my_app.organization",
                            ],
                            'exclude_models_from_import': [
                                "my_app.organizationdomainname",
                                "my_app.organizationuser",
                            ],
                        },
                    },
                }
            },
            main_settings,
        )
    )
```

### Requirements
This module requires the `multi_tenant` app from https://github.com/django-superapp/django-superapp-multi-tenant

## Management Commands

The backups app provides two management commands for synchronous backup and restore operations:

### create_backup

Creates a backup synchronously without using Celery.

**Usage:**
```bash
python manage.py create_backup --file <path> --backup-type <type> [options]
```

**Required Arguments:**
- `--file`: File path where the backup will be saved
- `--backup-type`: Type of backup to create (must be defined in BACKUPS.BACKUP_TYPES settings)

**Optional Arguments:**
- `--name`: Optional name for the backup (will be auto-generated if not provided)
- `--tenant-id`: Tenant ID for multi-tenant backups (if multi-tenant is enabled)

**Examples:**
```bash
# Create a backup with all models
python manage.py create_backup --file /path/to/backup.zip --backup-type all_models

# Create a backup with essential data only
python manage.py create_backup --file /path/to/backup.zip --backup-type essential_data

# Create a multi-tenant backup
python manage.py create_backup --file /path/to/backup.zip --backup-type all_models --tenant-id 1

# Create a backup with custom name
python manage.py create_backup --file /path/to/backup.zip --backup-type essential_data --name "Weekly Backup"
```

### restore_backup

Restores data synchronously from a backup file.

**Usage:**
```bash
python manage.py restore_backup --file <path> --backup-type <type> [options]
```

**Required Arguments:**
- `--file`: Path to backup file to restore (can be .zip or .json)
- `--backup-type`: Type of backup being restored (must be defined in BACKUPS.BACKUP_TYPES settings)

**Optional Arguments:**
- `--name`: Optional name for the restore operation (will be auto-generated if not provided)
- `--tenant-id`: Tenant ID for multi-tenant restores (if multi-tenant is enabled)
- `--cleanup-existing-data`: Clean up existing data before restoring (default: False)

**Examples:**
```bash
# Restore a backup
python manage.py restore_backup --file /path/to/backup.zip --backup-type all_models

# Restore with cleanup of existing data
python manage.py restore_backup --file /path/to/backup.zip --backup-type essential_data --cleanup-existing-data

# Restore a multi-tenant backup
python manage.py restore_backup --file /path/to/backup.zip --backup-type all_models --tenant-id 1

# Restore from JSON file
python manage.py restore_backup --file /path/to/backup.json --backup-type essential_data
```

## Makefile Commands

For convenience, a Makefile is provided with common backup operations:

```bash
# Navigate to the backups app directory
cd backend/superapp/apps/backups/

# Create a backup (saves to backend/backups/backup.zip)
make backup

# Create an essential data backup
make backup-essential

# Restore from backup
make restore

# Restore with cleanup of existing data
make restore-clean

# Show available commands
make help

# Show backup file information
make info

# Clean up backup files
make clean
```

## Backup Types

The available backup types are defined in `settings.py`:

- **all_models**: Backup all models in the database
- **essential_data**: Backup only essential data (specific models defined in settings)

You can add custom backup types by extending the `BACKUP_TYPES` configuration in your settings.

## Scheduled Backups Configuration

The app automatically configures scheduled backup tasks using Celery Beat. You can customize the schedule by modifying the settings:

### Automated Weekly Backup

By default, the app creates a weekly backup of essential data every Monday at 3 AM:

```python
# In your settings.py
CELERY_BEAT_SCHEDULE = {
    'backups-weekly-essential-backup': {
        'task': 'backups.automated_weekly_backup',
        'schedule': crontab(hour=3, minute=0, day_of_week=1),  # Weekly on Monday at 3 AM
    },
}
```

### Backup Cleanup Configuration

Configure automatic cleanup of old backups to maintain storage limits:

```python
# In your settings.py
BACKUPS = {
    'RETENTION': {
        'MAX_BACKUPS': 30,  # Keep only the 30 most recent backups
    },
    'BACKUP_TYPES': {
        # ... your backup types
    }
}
```

### Custom Backup Schedules

You can add custom backup schedules by extending the `CELERY_BEAT_SCHEDULE`:

```python
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE.update({
    # Daily backup at 2 AM
    'backups-daily-essential': {
        'task': 'backups.automated_weekly_backup',
        'schedule': crontab(hour=2, minute=0),
    },
    
    # Cleanup old backups weekly on Sunday at 4 AM
    'backups-cleanup-old': {
        'task': 'backups.cleanup_old_backups',
        'schedule': crontab(hour=4, minute=0, day_of_week=0),
    },
})
```

### Disabling Scheduled Tasks

To disable automatic scheduled task setup, set the environment variable:

```bash
export SETUP_SCHEDULED_TASKS=false
```

## Features

- **Media Files Support**: Both commands handle media files (images, documents) referenced by FileField and ImageField
- **Multi-tenant Support**: Compatible with django-superapp multi-tenant setup
- **ZIP Archives**: Creates compressed ZIP files containing JSON data and media files
- **Progress Reporting**: Detailed output showing backup/restore progress
- **Error Handling**: Comprehensive error handling with informative messages
- **Synchronous Operations**: No dependency on Celery for immediate execution
- **Automated Cleanup**: Configurable retention policy to manage storage usage

### Documentation
For a more detailed documentation, visit [https://django-superapp.bringes.io](https://django-superapp.bringes.io).
