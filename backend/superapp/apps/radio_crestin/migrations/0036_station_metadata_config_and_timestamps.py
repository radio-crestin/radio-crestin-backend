from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('radio_crestin', '0035_rename_generate_hls_stream_to_transcode_enabled'),
    ]

    operations = [
        # Station: metadata timestamp source config
        migrations.AddField(
            model_name='stations',
            name='metadata_timestamp_source',
            field=models.CharField(
                choices=[
                    ('mel_analysis', 'Mel Spectrogram Analysis'),
                    ('id3_metadata', 'ID3 Stream Metadata'),
                    ('scraper', 'External Scraper (periodic)'),
                ],
                default='scraper',
                help_text='Which detection method triggers metadata scraping: mel analysis (audio change), ID3 tags, or periodic scraper interval',
                max_length=20,
                verbose_name='Metadata Timestamp Source',
            ),
        ),
        migrations.AddField(
            model_name='stations',
            name='metadata_scrape_interval',
            field=models.IntegerField(
                default=30,
                help_text="How often to scrape metadata when using 'scraper' timestamp source",
                verbose_name='Metadata Scrape Interval (seconds)',
            ),
        ),
        migrations.AddField(
            model_name='stations',
            name='id3_metadata_delay_offset',
            field=models.FloatField(
                default=0.0,
                help_text='Time offset to shift ID3 metadata timing (positive = delay, negative = advance)',
                verbose_name='ID3 Metadata Delay Offset (seconds)',
            ),
        ),
        migrations.AddField(
            model_name='stations',
            name='config_version',
            field=models.PositiveIntegerField(
                default=1,
                help_text='Incremented on config changes to notify streaming pods to reload',
                verbose_name='Config Version',
            ),
        ),
        # StationsNowPlaying: thumbnail_url
        migrations.AddField(
            model_name='stationsnowplaying',
            name='thumbnail_url',
            field=models.URLField(
                blank=True,
                null=True,
                help_text='Current song thumbnail for real-time HLS metadata embedding',
                verbose_name='Thumbnail URL',
            ),
        ),
        # StationsNowPlayingHistory: multiple timestamp sources
        migrations.AddField(
            model_name='stationsnowplayinghistory',
            name='mel_timestamp',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text='When mel spectrogram analysis detected a song change',
                verbose_name='Mel Analysis Timestamp',
            ),
        ),
        migrations.AddField(
            model_name='stationsnowplayinghistory',
            name='id3_timestamp',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text='When ID3 stream metadata indicated a song change',
                verbose_name='ID3 Metadata Timestamp',
            ),
        ),
        migrations.AddField(
            model_name='stationsnowplayinghistory',
            name='scraper_timestamp',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text='When external metadata scraper detected a song change',
                verbose_name='Scraper Timestamp',
            ),
        ),
        migrations.AddField(
            model_name='stationsnowplayinghistory',
            name='timestamp_source',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Which source triggered this history entry (mel_analysis, id3_metadata, scraper)',
                max_length=20,
                verbose_name='Timestamp Source',
            ),
        ),
    ]
