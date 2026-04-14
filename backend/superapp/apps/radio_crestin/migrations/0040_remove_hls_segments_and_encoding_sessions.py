from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('radio_crestin', '0039_create_hls_encoding_sessions'),
    ]

    operations = [
        migrations.DeleteModel(
            name='HlsSegment',
        ),
        migrations.DeleteModel(
            name='HlsEncodingSession',
        ),
    ]
