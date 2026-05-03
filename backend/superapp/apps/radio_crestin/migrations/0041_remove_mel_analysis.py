from django.db import migrations, models


def remove_mel_category(apps, schema_editor):
    """Drop the mel_analysis category. The FK on StationMetadataFetches is
    on_delete=CASCADE, so any fetch rows wired to mel_analysis will be
    removed alongside the category — they are useless without the
    (now-deleted) mel_analyzer process anyway.
    """
    StationMetadataFetchCategories = apps.get_model('radio_crestin', 'StationMetadataFetchCategories')
    StationMetadataFetches = apps.get_model('radio_crestin', 'StationMetadataFetches')
    # Delete dependent rows explicitly (audit-friendly: visible in migration
    # output instead of hidden inside a cascade).
    StationMetadataFetches.objects.filter(
        station_metadata_fetch_category__slug='mel_analysis'
    ).delete()
    StationMetadataFetchCategories.objects.filter(slug='mel_analysis').delete()


def restore_mel_category(apps, schema_editor):
    StationMetadataFetchCategories = apps.get_model('radio_crestin', 'StationMetadataFetchCategories')
    StationMetadataFetchCategories.objects.get_or_create(slug='mel_analysis')


def reset_mel_timestamp_source(apps, schema_editor):
    Stations = apps.get_model('radio_crestin', 'Stations')
    Stations.objects.filter(metadata_timestamp_source='mel_analysis').update(
        metadata_timestamp_source='scraper'
    )


class Migration(migrations.Migration):

    dependencies = [
        ('radio_crestin', '0040_remove_hls_segments_and_encoding_sessions'),
    ]

    operations = [
        migrations.RunPython(reset_mel_timestamp_source, migrations.RunPython.noop),
        migrations.RunPython(remove_mel_category, restore_mel_category),
        migrations.RemoveField(
            model_name='stationsnowplayinghistory',
            name='mel_timestamp',
        ),
        migrations.AlterField(
            model_name='stations',
            name='metadata_timestamp_source',
            field=models.CharField(
                choices=[
                    ('id3_metadata', 'ID3 Stream Metadata'),
                    ('scraper', 'External Scraper (periodic)'),
                ],
                default='scraper',
                help_text='Which detection method triggers metadata scraping: ID3 tags or periodic scraper interval',
                max_length=20,
                verbose_name='Metadata Timestamp Source',
            ),
        ),
    ]
