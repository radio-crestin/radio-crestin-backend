from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from deepmerge import always_merger

def extend_superapp_settings(main_settings):
    main_settings['INSTALLED_APPS'] = [
        'superapp.apps.backups',
    ] + main_settings['INSTALLED_APPS']


    main_settings.update(
        always_merger.merge(
            {
                'BACKUPS': {
                    'BACKUP_TYPES': {
                        'all_models': {
                            'name': _('All Models'),
                            'description': _('Backup all models'),
                            'models': '*',
                            'exclude_models_from_import': [],
                        },
                        'essential_data': {
                            'name': _('Essential Data'),
                            'description': _('Backup essential data only'),
                            'models': [
                                'radio_crestin.stationsmetadatafetch',
                                'radio_crestin.stationtostationgroup',
                                'radio_crestin.stationstreams',
                                'radio_crestin.reviews',
                                'radio_crestin.posts',
                                'radio_crestin.stationsuptime',
                                'radio_crestin.stationsnowplaying',
                                'radio_crestin.stations',
                                'radio_crestin.stationgroups',
                                'radio_crestin.stationmetadatafetchcategories',
                            ],
                            'exclude_models_from_import': [],
                            'schedule': {
                                'enabled': True,
                                'hour': 3,
                                'minute': 0,
                                'day_of_week': 1,  # Monday
                            },
                        },
                    },
                    'RETENTION': {
                        'MAX_BACKUPS': 30,
                    },
                }
            },
            main_settings,
        )
    )
    main_settings['UNFOLD']['SIDEBAR']['navigation'] += [
        {
            "title": _("Backups"),
            "icon": "database",
            "items": [
                {
                    "title": _("Backups"),
                    "icon": "backup",
                    "link": reverse_lazy("admin:backups_backup_changelist"),
                    "permission": lambda request: request.user.has_perm('backups.view_backup'),
                },
                {
                    "title": _("Restores"),
                    "icon": "restart_alt",
                    "link": reverse_lazy("admin:backups_restore_changelist"),
                    "permission": lambda request: request.user.has_perm('backups.view_restore'),
                },
            ]
        }
    ]

    # Configure Celery Beat schedule for backup tasks
    import os
    setup_scheduled_tasks = os.getenv('SETUP_SCHEDULED_TASKS', 'true').lower() == 'true'
    
    if setup_scheduled_tasks:
        from celery.schedules import crontab
        
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
