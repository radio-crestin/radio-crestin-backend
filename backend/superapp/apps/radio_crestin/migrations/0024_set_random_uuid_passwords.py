# Generated manually to set random UUID passwords for null values

from django.db import migrations
import uuid


def set_random_passwords(apps, schema_editor):
    AppUsers = apps.get_model('radio_crestin', 'AppUsers')
    users_with_null_password = AppUsers.objects.filter(password__isnull=True)
    
    for user in users_with_null_password:
        user.password = str(uuid.uuid4())
        user.save(update_fields=['password'])


def reverse_func(apps, schema_editor):
    # We can't really reverse this operation meaningfully
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('radio_crestin', '0023_remove_station_from_sharelink'),
    ]

    operations = [
        migrations.RunPython(set_random_passwords, reverse_func),
    ]