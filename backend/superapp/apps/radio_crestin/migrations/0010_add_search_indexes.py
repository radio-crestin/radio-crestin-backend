# Generated for autocomplete performance optimization
from django.db import migrations
from django.contrib.postgres.operations import TrigramExtension


class Migration(migrations.Migration):

    dependencies = [
        ('radio_crestin', '0009_alter_stationsmetadatafetch_options_and_more'),
    ]

    operations = [
        TrigramExtension(),
        migrations.RunSQL(
            sql=[
                # Add trigram indexes for fast text search on Songs.name
                "CREATE INDEX IF NOT EXISTS songs_name_trgm_idx ON songs USING gin (name gin_trgm_ops);",
                # Add trigram indexes for fast text search on Artists.name  
                "CREATE INDEX IF NOT EXISTS artists_name_trgm_idx ON artists USING gin (name gin_trgm_ops);",
            ],
            reverse_sql=[
                "DROP INDEX IF EXISTS songs_name_trgm_idx;",
                "DROP INDEX IF EXISTS artists_name_trgm_idx;", 
            ]
        )
    ]