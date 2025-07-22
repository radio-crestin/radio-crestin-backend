"""
Backup scheduling utilities for Celery Beat configuration.
"""
import os
import logging

logger = logging.getLogger(__name__)


def setup_backup_schedules(main_settings):
    """
    Configure Celery Beat schedules for backup tasks based on backup type configurations.
    
    Args:
        main_settings: Django settings dictionary to update
    """
    setup_scheduled_tasks = os.getenv('SETUP_SCHEDULED_TASKS', 'true').lower() == 'true'
    
    if not setup_scheduled_tasks:
        logger.info("Scheduled tasks disabled by SETUP_SCHEDULED_TASKS environment variable")
        return
    
    try:
        from celery.schedules import crontab
    except ImportError:
        logger.warning("Celery not installed, skipping backup schedule setup")
        return
    
    # Initialize CELERY_BEAT_SCHEDULE if it doesn't exist
    if 'CELERY_BEAT_SCHEDULE' not in main_settings:
        main_settings['CELERY_BEAT_SCHEDULE'] = {}
    
    # Dynamically add backup tasks based on backup type schedules
    backup_types = main_settings.get('BACKUPS', {}).get('BACKUP_TYPES', {})
    
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
            
            logger.info(f"Configured scheduled backup for {backup_type}: {schedule_kwargs}")


def remove_backup_schedules(main_settings):
    """
    Remove all backup-related scheduled tasks from Celery Beat configuration.
    
    Args:
        main_settings: Django settings dictionary to update
    """
    if 'CELERY_BEAT_SCHEDULE' not in main_settings:
        return
    
    # Remove all backup-related scheduled tasks
    tasks_to_remove = [
        task_name for task_name in main_settings['CELERY_BEAT_SCHEDULE'].keys()
        if task_name.startswith('backups-scheduled-')
    ]
    
    for task_name in tasks_to_remove:
        del main_settings['CELERY_BEAT_SCHEDULE'][task_name]
        logger.info(f"Removed scheduled backup task: {task_name}")
    
    if tasks_to_remove:
        logger.info(f"Removed {len(tasks_to_remove)} backup scheduled tasks")