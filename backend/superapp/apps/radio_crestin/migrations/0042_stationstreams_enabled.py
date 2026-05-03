from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('radio_crestin', '0041_remove_mel_analysis'),
    ]

    operations = [
        migrations.AddField(
            model_name='stationstreams',
            name='enabled',
            field=models.BooleanField(default=True, verbose_name='Enabled'),
        ),
    ]
