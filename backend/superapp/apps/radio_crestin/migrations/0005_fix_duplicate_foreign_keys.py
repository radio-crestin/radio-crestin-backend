from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('radio_crestin', '0004_fix_users_table_and_foreign_keys'),
    ]

    operations = [
        # Remove the old Django foreign key constraints that point to authentication_user
        migrations.RunSQL(
            sql="""
            ALTER TABLE listening_events 
            DROP CONSTRAINT IF EXISTS listening_events_user_id_3170c89a_fk_authentication_user_id;
            
            ALTER TABLE reviews 
            DROP CONSTRAINT IF EXISTS reviews_user_id_c23b0903_fk_authentication_user_id;
            """,
            reverse_sql="""
            ALTER TABLE listening_events 
            ADD CONSTRAINT listening_events_user_id_3170c89a_fk_authentication_user_id 
            FOREIGN KEY (user_id) REFERENCES authentication_user(id) DEFERRABLE INITIALLY DEFERRED;
            
            ALTER TABLE reviews 
            ADD CONSTRAINT reviews_user_id_c23b0903_fk_authentication_user_id 
            FOREIGN KEY (user_id) REFERENCES authentication_user(id) DEFERRABLE INITIALLY DEFERRED;
            """,
        ),
    ]