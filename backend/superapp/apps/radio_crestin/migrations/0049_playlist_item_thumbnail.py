from django.db import migrations, models

import superapp.apps.storage.config


class Migration(migrations.Migration):
    """Add an optional uploaded thumbnail to StationPlaylistItems.

    Mirrors the Stations.thumbnail conventions (public storage backend,
    per-model upload path). APIs keep serving the `thumbnail_url` wire field,
    resolved server-side: uploaded image URL if present, else the manual URL.
    """

    dependencies = [
        ('radio_crestin', '0048_stations_playlist_api_key'),
    ]

    operations = [
        migrations.AddField(
            model_name='stationplaylistitems',
            name='thumbnail',
            field=models.ImageField(
                blank=True,
                null=True,
                storage=superapp.apps.storage.config.get_public_storage,
                upload_to='playlist_items/',
                verbose_name='Thumbnail',
            ),
        ),
    ]
