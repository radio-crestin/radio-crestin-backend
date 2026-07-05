import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('radio_crestin', '0044_appusers_device_details'),
    ]

    operations = [
        migrations.AddField(
            model_name='stations',
            name='station_type',
            field=models.CharField(
                choices=[('radio', 'Radio'), ('tv', 'TV'), ('playlist', 'Playlist')],
                default='radio',
                help_text='Radio stream, TV stream, or a managed playlist of media items',
                max_length=16,
                verbose_name='Station Type',
            ),
        ),
        migrations.CreateModel(
            name='StationPlaylistItems',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('type', models.CharField(choices=[('audio', 'Audio'), ('video', 'Video'), ('youtube', 'YouTube')], default='audio', max_length=16, verbose_name='Type')),
                ('url', models.TextField(help_text='Media URL — direct MP3/AAC/MP4 file, HLS .m3u8, or a full YouTube link', verbose_name='Media URL')),
                ('title', models.TextField(blank=True, default='', verbose_name='Title')),
                ('thumbnail_url', models.URLField(blank=True, null=True, verbose_name='Thumbnail URL')),
                ('duration_seconds', models.IntegerField(blank=True, null=True, verbose_name='Duration (seconds)')),
                ('order', models.IntegerField(default=0, verbose_name='Order')),
                ('playlist_item_order', models.FloatField(default=0, verbose_name='Playlist Item Order')),
                ('enabled', models.BooleanField(default=True, verbose_name='Enabled')),
                ('station', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='playlist_items', to='radio_crestin.stations', verbose_name='Station')),
            ],
            options={
                'verbose_name': 'Station Playlist Item',
                'verbose_name_plural': 'Station Playlist Items',
                'db_table': 'station_playlist_items',
                'ordering': ('station', 'playlist_item_order'),
                'managed': True,
            },
        ),
    ]
