from django.db import migrations


def remove_duplicate_anonymous_ids(apps, schema_editor):
    """
    Remove duplicate AppUsers records with the same anonymous_id,
    keeping only the oldest record (by id) for each anonymous_id.
    """
    from django.db import connection

    with connection.cursor() as cursor:
        # Find and delete duplicate records, keeping the one with the lowest id
        cursor.execute("""
            DELETE FROM app_users
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM app_users
                GROUP BY anonymous_id
            )
        """)
        deleted_count = cursor.rowcount
        if deleted_count > 0:
            print(f"Removed {deleted_count} duplicate AppUsers records")


def noop(apps, schema_editor):
    """No-op reverse migration - duplicates cannot be recreated."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('radio_crestin', '0027_alter_artists_thumbnail_alter_songs_thumbnail_and_more'),
    ]

    operations = [
        migrations.RunPython(remove_duplicate_anonymous_ids, noop),
    ]
