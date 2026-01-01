from django.db import migrations


def remove_duplicate_anonymous_ids(apps, schema_editor):
    """
    Remove duplicate AppUsers records with the same anonymous_id,
    keeping only the oldest record (by id) for each anonymous_id.
    Also handles related share_links by reassigning them to the kept user.
    """
    from django.db import connection

    with connection.cursor() as cursor:
        # First, find all duplicate anonymous_ids and their users
        # For each duplicate group, reassign share_links to the user we're keeping (lowest id)
        cursor.execute("""
            WITH duplicates AS (
                SELECT anonymous_id, MIN(id) as keep_id
                FROM app_users
                WHERE anonymous_id IS NOT NULL
                GROUP BY anonymous_id
                HAVING COUNT(*) > 1
            ),
            users_to_delete AS (
                SELECT au.id as delete_id, d.keep_id
                FROM app_users au
                JOIN duplicates d ON au.anonymous_id = d.anonymous_id
                WHERE au.id != d.keep_id
            )
            UPDATE share_links sl
            SET user_id = utd.keep_id
            FROM users_to_delete utd
            WHERE sl.user_id = utd.delete_id
        """)
        reassigned_count = cursor.rowcount
        if reassigned_count > 0:
            print(f"Reassigned {reassigned_count} share_links to kept users")

        # Also handle share_link_visits if they reference users
        cursor.execute("""
            WITH duplicates AS (
                SELECT anonymous_id, MIN(id) as keep_id
                FROM app_users
                WHERE anonymous_id IS NOT NULL
                GROUP BY anonymous_id
                HAVING COUNT(*) > 1
            ),
            users_to_delete AS (
                SELECT au.id as delete_id, d.keep_id
                FROM app_users au
                JOIN duplicates d ON au.anonymous_id = d.anonymous_id
                WHERE au.id != d.keep_id
            )
            DELETE FROM share_links
            WHERE user_id IN (SELECT delete_id FROM users_to_delete)
        """)
        deleted_links = cursor.rowcount
        if deleted_links > 0:
            print(f"Deleted {deleted_links} orphaned share_links from duplicate users")

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
