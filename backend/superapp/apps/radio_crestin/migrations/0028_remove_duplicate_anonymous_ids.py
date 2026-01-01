from django.db import migrations


def remove_duplicate_anonymous_ids(apps, schema_editor):
    """
    Remove duplicate AppUsers records with the same anonymous_id,
    keeping only the oldest record (by id) for each anonymous_id.
    Deletes share_links from duplicate users (since user_id has a unique constraint).
    """
    from django.db import connection

    with connection.cursor() as cursor:
        # Delete share_links from duplicate users (can't reassign due to unique constraint on user_id)
        cursor.execute("""
            WITH duplicates AS (
                SELECT anonymous_id, MIN(id) as keep_id
                FROM app_users
                WHERE anonymous_id IS NOT NULL
                GROUP BY anonymous_id
                HAVING COUNT(*) > 1
            ),
            users_to_delete AS (
                SELECT au.id as delete_id
                FROM app_users au
                JOIN duplicates d ON au.anonymous_id = d.anonymous_id
                WHERE au.id != d.keep_id
            )
            DELETE FROM share_links
            WHERE user_id IN (SELECT delete_id FROM users_to_delete)
        """)
        deleted_links = cursor.rowcount
        if deleted_links > 0:
            print(f"Deleted {deleted_links} share_links from duplicate users")

        # Now delete the duplicate app_users records
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
