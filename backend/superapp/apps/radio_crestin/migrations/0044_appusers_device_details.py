from django.db import migrations, models


class Migration(migrations.Migration):
    """Add nullable device-registration columns to app_users.

    All fields are nullable, so this is a non-destructive, online-safe migration
    that does not affect existing rows or the separate authentication user table.
    Populated by POST /api/v1/devices/register/ (update_or_create on anonymous_id).
    """

    dependencies = [
        ('radio_crestin', '0043_session_recording'),
    ]

    operations = [
        migrations.AddField(
            model_name='appusers',
            name='device_platform',
            field=models.CharField(blank=True, max_length=64, null=True, verbose_name='Device platform'),
        ),
        migrations.AddField(
            model_name='appusers',
            name='device_model',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Device model'),
        ),
        migrations.AddField(
            model_name='appusers',
            name='device_manufacturer',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Device manufacturer'),
        ),
        migrations.AddField(
            model_name='appusers',
            name='device_os_version',
            field=models.CharField(blank=True, max_length=64, null=True, verbose_name='OS version'),
        ),
        migrations.AddField(
            model_name='appusers',
            name='device_app_version',
            field=models.CharField(blank=True, max_length=64, null=True, verbose_name='App version'),
        ),
        migrations.AddField(
            model_name='appusers',
            name='device_build_number',
            field=models.CharField(blank=True, max_length=64, null=True, verbose_name='App build number'),
        ),
        migrations.AddField(
            model_name='appusers',
            name='device_locale',
            field=models.CharField(blank=True, max_length=64, null=True, verbose_name='Locale'),
        ),
        migrations.AddField(
            model_name='appusers',
            name='device_timezone',
            field=models.CharField(blank=True, max_length=64, null=True, verbose_name='Timezone'),
        ),
        migrations.AddField(
            model_name='appusers',
            name='device_is_physical',
            field=models.BooleanField(blank=True, null=True, verbose_name='Is physical device'),
        ),
        migrations.AddField(
            model_name='appusers',
            name='device_fcm_token',
            field=models.TextField(blank=True, null=True, verbose_name='FCM push token'),
        ),
        migrations.AddField(
            model_name='appusers',
            name='device_last_ip',
            field=models.GenericIPAddressField(blank=True, null=True, verbose_name='Last IP address'),
        ),
        migrations.AddField(
            model_name='appusers',
            name='device_info',
            field=models.JSONField(blank=True, null=True, verbose_name='Raw device info'),
        ),
        migrations.AddField(
            model_name='appusers',
            name='device_first_seen_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Device first seen at'),
        ),
        migrations.AddField(
            model_name='appusers',
            name='device_last_seen_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Device last seen at'),
        ),
    ]
