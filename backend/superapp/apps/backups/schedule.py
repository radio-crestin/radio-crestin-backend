"""
Backup scheduling utilities for Celery Beat configuration.
"""
import logging

logger = logging.getLogger(__name__)


def setup_backup_schedules(main_settings):
    """
    Configure Celery Beat schedules for backup tasks based on backup type configurations.
    Automatically removes schedules that are no longer enabled or defined.
    Also manages PeriodicTask records in the database, disabling tasks that are not enabled.
    
    Args:
        main_settings: Django settings dictionary to update
    """
    # Initialize CELERY_BEAT_SCHEDULE if it doesn't exist
    if 'CELERY_BEAT_SCHEDULE' not in main_settings:
        main_settings['CELERY_BEAT_SCHEDULE'] = {}
    
    # First, remove all existing backup schedules to clean up disabled/removed ones
    tasks_to_remove = [
        task_name for task_name in main_settings['CELERY_BEAT_SCHEDULE'].keys()
        if task_name.startswith('backups-scheduled-')
    ]
    
    for task_name in tasks_to_remove:
        del main_settings['CELERY_BEAT_SCHEDULE'][task_name]
        logger.debug(f"Removed existing scheduled backup task: {task_name}")
    
    if tasks_to_remove:
        logger.info(f"Cleaned up {len(tasks_to_remove)} existing backup scheduled tasks")
    
    # Note: PeriodicTask database management is handled by the ready() method in apps.py
    # to avoid importing Django models during settings configuration
    
    try:
        from celery.schedules import crontab
    except ImportError:
        logger.warning("Celery not installed, skipping backup schedule setup")
        return
    
    # Add enabled backup tasks based on backup type schedules
    backup_types = main_settings.get('BACKUPS', {}).get('BACKUP_TYPES', {})
    enabled_count = 0
    
    for backup_type, config in backup_types.items():
        schedule_config = config.get('schedule')
        if schedule_config and schedule_config.get('enabled', False):
            task_name = f'backups-scheduled-{backup_type}-backup'
            
            # Create crontab schedule from configuration
            schedule_kwargs = {}
            if 'hour' in schedule_config:
                schedule_kwargs['hour'] = schedule_config['hour']
            if 'minute' in schedule_config:
                schedule_kwargs['minute'] = schedule_config['minute']
            if 'day_of_week' in schedule_config:
                schedule_kwargs['day_of_week'] = schedule_config['day_of_week']
            if 'day_of_month' in schedule_config:
                schedule_kwargs['day_of_month'] = schedule_config['day_of_month']
            
            main_settings['CELERY_BEAT_SCHEDULE'][task_name] = {
                'task': 'backups.automated_backup',
                'schedule': crontab(**schedule_kwargs),
                'kwargs': {'backup_type': backup_type},
            }
            
            enabled_count += 1
            logger.info(f"Configured scheduled backup for {backup_type}: {schedule_kwargs}")
    
    logger.info(f"Backup schedule setup complete: {enabled_count} scheduled backups enabled")


def manage_periodic_tasks():
    """
    Manage PeriodicTask records in the database, disabling backup tasks that are not enabled.
    This should be called from apps.py ready() method after Django is fully initialized.
    """
    try:
        from django_celery_beat.models import PeriodicTask
        from django.conf import settings
        from django.db import connection
    except ImportError:
        logger.debug("django_celery_beat not installed, skipping PeriodicTask management")
        return
    
    try:
        # Check if the database table exists before querying
        table_names = connection.introspection.table_names()
        if 'django_celery_beat_periodictask' not in table_names:
            logger.debug("django_celery_beat_periodictask table not found, skipping PeriodicTask management")
            return
        
        # Get all backup-related periodic tasks from database
        backup_tasks = PeriodicTask.objects.filter(name__startswith='backups-scheduled-')
        
        if not backup_tasks.exists():
            logger.debug("No backup PeriodicTasks found in database")
            return
        
        # Get currently enabled backup types
        backup_types = getattr(settings, 'BACKUPS', {}).get('BACKUP_TYPES', {})
        enabled_tasks = set()
        
        for backup_type, config in backup_types.items():
            schedule_config = config.get('schedule')
            if schedule_config and schedule_config.get('enabled', False):
                task_name = f'backups-scheduled-{backup_type}-backup'
                enabled_tasks.add(task_name)
        
        # Process each backup task in database
        disabled_count = 0
        enabled_count = 0
        
        for task in backup_tasks:
            if task.name in enabled_tasks:
                # Task should be enabled
                if not task.enabled:
                    task.enabled = True
                    task.save(update_fields=['enabled'])
                    enabled_count += 1
                    logger.info(f"Enabled PeriodicTask: {task.name}")
            else:
                # Task should be disabled
                if task.enabled:
                    task.enabled = False
                    task.save(update_fields=['enabled'])
                    disabled_count += 1
                    logger.info(f"Disabled PeriodicTask: {task.name}")
        
        if disabled_count > 0 or enabled_count > 0:
            logger.info(f"PeriodicTask management complete: {enabled_count} enabled, {disabled_count} disabled")
            
    except Exception as e:
        logger.warning(f"Error managing PeriodicTask records: {e}")