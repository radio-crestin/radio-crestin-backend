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
                                "my_app.model1",
                                "my_app.model2",
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
```

### Requirements
This module requires the `tasks` app from https://github.com/django-superapp/django-superapp-tasks

### Optional Requirements  
The `multi_tenant` app from https://github.com/django-superapp/django-superapp-multi-tenant is optional for multi-tenant support

## Management Commands

```bash
# Create backup
docker-compose run web python3 manage.py create_backup --file backups/backup.zip --backup-type all_models

# Restore backup
docker-compose run web python3 manage.py restore_backup --file backups/backup.zip --backup-type all_models
```

### Documentation
For a more detailed documentation, visit [https://django-superapp.bringes.io](https://django-superapp.bringes.io).
