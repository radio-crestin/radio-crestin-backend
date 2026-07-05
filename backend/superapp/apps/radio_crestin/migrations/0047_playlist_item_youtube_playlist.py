from django.db import migrations, models


class Migration(migrations.Migration):
    """Add the `youtube_playlist` choice to StationPlaylistItems.type.

    Choices-only change ('youtube_playlist' fits the existing max_length=16),
    so this does not alter the database column.
    """

    dependencies = [
        ('radio_crestin', '0046_station_visibility'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stationplaylistitems',
            name='type',
            field=models.CharField(
                choices=[
                    ('audio', 'Audio'),
                    ('video', 'Video'),
                    ('youtube', 'YouTube'),
                    ('youtube_playlist', 'YouTube Playlist'),
                ],
                default='audio',
                max_length=16,
                verbose_name='Type',
            ),
        ),
    ]
