from django.db import migrations


def add_mel_analysis_category(apps, schema_editor):
    StationMetadataFetchCategories = apps.get_model('radio_crestin', 'StationMetadataFetchCategories')
    StationMetadataFetchCategories.objects.get_or_create(slug='mel_analysis')


def remove_mel_analysis_category(apps, schema_editor):
    StationMetadataFetchCategories = apps.get_model('radio_crestin', 'StationMetadataFetchCategories')
    StationMetadataFetchCategories.objects.filter(slug='mel_analysis').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('radio_crestin', '0036_station_metadata_config_and_timestamps'),
    ]

    operations = [
        migrations.RunPython(add_mel_analysis_category, remove_mel_analysis_category),
    ]
