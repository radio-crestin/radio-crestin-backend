from django.db import migrations, models


class Migration(migrations.Migration):
    """Per-station API key authorizing external playlist updates.

    Blank by default; `Stations.save()` auto-generates a key for
    playlist-type stations, so existing playlist stations get one on their
    next save and radio/tv stations keep an empty key.
    """

    dependencies = [
        ('radio_crestin', '0047_playlist_item_youtube_playlist'),
    ]

    operations = [
        migrations.AddField(
            model_name='stations',
            name='playlist_api_key',
            field=models.CharField(
                blank=True,
                db_index=True,
                default='',
                help_text='Authorizes external playlist updates for this station only (X-Api-Key header on POST /api/v1/station-playlist/update). Auto-generated for playlist stations.',
                max_length=64,
                verbose_name='Playlist API Key',
            ),
        ),
    ]
