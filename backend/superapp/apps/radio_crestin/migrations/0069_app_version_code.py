from django.db import migrations, models

from superapp.apps.radio_crestin.utils.app_versions import version_code


def fill_version_codes(apps, schema_editor):
    """One UPDATE per distinct version string (a few dozen), not one per device."""
    AppUsers = apps.get_model('radio_crestin', 'AppUsers')
    versions = (AppUsers.objects.exclude(device_app_version__isnull=True).exclude(device_app_version='')
                .order_by().values_list('device_app_version', flat=True).distinct())
    for version in list(versions):
        code = version_code(version)
        if code is not None:
            AppUsers.objects.filter(device_app_version=version).update(device_app_version_code=code)


class Migration(migrations.Migration):
    # The backfill and the column change can't share one Postgres transaction
    # ("pending trigger events"), so each operation runs on its own.
    atomic = False

    dependencies = [
        ('radio_crestin', '0068_announcement_icon_size'),
    ]

    operations = [
        migrations.AddField(
            model_name='appusers',
            name='device_app_version_code',
            field=models.BigIntegerField(blank=True, db_index=True, null=True, verbose_name='App version code'),
        ),
        migrations.RunPython(fill_version_codes, migrations.RunPython.noop),
    ]
