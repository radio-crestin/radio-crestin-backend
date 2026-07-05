from django.db import migrations, models


class Migration(migrations.Migration):
    """Per-station public/private visibility with a device allowlist.

    `is_public` defaults to True so all existing stations stay visible.
    `visible_to_devices` allowlists AppUsers (matched by anonymous_id ==
    the app's device id) that may see a station when it is not public.
    """

    dependencies = [
        ('radio_crestin', '0045_station_type_and_playlist_items'),
    ]

    operations = [
        migrations.AddField(
            model_name='stations',
            name='is_public',
            field=models.BooleanField(
                default=True,
                help_text='Public stations appear in all public APIs. Private stations are only visible to the allowlisted devices below.',
                verbose_name='Public',
            ),
        ),
        migrations.AddField(
            model_name='stations',
            name='visible_to_devices',
            field=models.ManyToManyField(
                blank=True,
                db_table='station_visible_to_devices',
                help_text='Devices (matched by anonymous_id) allowed to see this station when it is not public.',
                related_name='private_stations',
                to='radio_crestin.appusers',
                verbose_name='Visible to Devices',
            ),
        ),
    ]
