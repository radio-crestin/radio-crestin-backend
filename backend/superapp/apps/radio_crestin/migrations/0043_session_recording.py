import django.core.validators
from django.db import migrations, models


def create_default_config(apps, schema_editor):
    """Seed a single disabled config row so it can be edited in the admin."""
    Config = apps.get_model('radio_crestin', 'SessionRecordingConfig')
    if not Config.objects.exists():
        Config.objects.create(enabled=False, rollout_percentage=0, sample_rate=1.0)


class Migration(migrations.Migration):

    dependencies = [
        ('radio_crestin', '0042_stationstreams_enabled'),
    ]

    operations = [
        migrations.CreateModel(
            name='SessionRecordingConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('enabled', models.BooleanField(default=False, help_text='Master switch. When off, only manual force-on overrides record.', verbose_name='Enabled')),
                ('rollout_percentage', models.PositiveSmallIntegerField(default=0, help_text='Percent of devices (0-100) that record, chosen deterministically by device id.', validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)], verbose_name='Rollout percentage')),
                ('sample_rate', models.FloatField(default=1.0, help_text='PostHog sample rate (0.0-1.0) within recorded sessions. Usually 1.0.', validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(1.0)], verbose_name='Sample rate')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Session Recording Config',
                'verbose_name_plural': 'Session Recording Config',
                'db_table': 'session_recording_config',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='SessionRecordingOverride',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('device_id', models.CharField(help_text="The device's anonymous id (the device_id the app sends).", max_length=512, unique=True, verbose_name='Device ID')),
                ('enabled', models.BooleanField(default=True, help_text='Force recording ON (checked) or OFF (unchecked) for this device.', verbose_name='Record')),
                ('note', models.CharField(blank=True, default='', max_length=255, verbose_name='Note')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Session Recording Override',
                'verbose_name_plural': 'Session Recording Overrides',
                'db_table': 'session_recording_override',
                'managed': True,
            },
        ),
        migrations.RunPython(create_default_config, migrations.RunPython.noop),
    ]
