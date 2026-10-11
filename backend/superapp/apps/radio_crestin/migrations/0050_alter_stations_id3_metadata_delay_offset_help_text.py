from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('radio_crestin', '0049_playlist_item_thumbnail'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stations',
            name='id3_metadata_delay_offset',
            field=models.FloatField(default=0.0, help_text="Seconds the stream's ID3/ICY title arrives after the audio change. Positive: the title arrives late, so the song is dated earlier by this much. Negative: the title arrives early, so the song is dated later. Applied to the API history and to the HLS playlist tags alike. Keep it within ±30: songs are never dated more than 45 s before they are reported.", verbose_name='ID3 Metadata Delay Offset (seconds)'),
        ),
    ]
