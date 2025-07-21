from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('radio_crestin', '0003_create_users_view_and_computed_functions'),
    ]

    operations = [
        # Drop the users view first
        migrations.RunSQL(
            sql="DROP VIEW IF EXISTS users;",
            reverse_sql="",
        ),
        
        # Create users table as a proper table that mirrors authentication_user
        migrations.RunSQL(
            sql="""
            CREATE TABLE users (
                id integer PRIMARY KEY,
                password varchar(128) NOT NULL DEFAULT '',
                last_login timestamptz,
                is_superuser boolean NOT NULL DEFAULT false,
                first_name varchar(150) NOT NULL DEFAULT '',
                last_name varchar(150) NOT NULL DEFAULT '',
                email varchar(254),
                is_staff boolean NOT NULL DEFAULT true,
                is_active boolean NOT NULL DEFAULT true,
                date_joined timestamptz NOT NULL DEFAULT now(),
                anonymous_id varchar(512),
                anonymous_id_verified timestamptz,
                email_verified timestamptz,
                phone_number varchar(255),
                phone_number_verified timestamptz,
                checkout_phone_number varchar(255),
                photo_url varchar(255),
                address varchar(1024),
                created_at timestamptz NOT NULL DEFAULT now(),
                modified_at timestamptz NOT NULL DEFAULT now()
            );
            """,
            reverse_sql="DROP TABLE IF EXISTS users;",
        ),
        
        # Create unique constraints on users table
        migrations.RunSQL(
            sql="""
            ALTER TABLE users ADD CONSTRAINT unique_users_email 
                UNIQUE (email) DEFERRABLE INITIALLY DEFERRED;
            ALTER TABLE users ADD CONSTRAINT unique_users_phone_number 
                UNIQUE (phone_number) DEFERRABLE INITIALLY DEFERRED;
            ALTER TABLE users ADD CONSTRAINT unique_users_anonymous_id 
                UNIQUE (anonymous_id) DEFERRABLE INITIALLY DEFERRED;
            """,
            reverse_sql="""
            ALTER TABLE users DROP CONSTRAINT IF EXISTS unique_users_email;
            ALTER TABLE users DROP CONSTRAINT IF EXISTS unique_users_phone_number;
            ALTER TABLE users DROP CONSTRAINT IF EXISTS unique_users_anonymous_id;
            """,
        ),
        
        # Create function to sync users table with authentication_user
        migrations.RunSQL(
            sql="""
            CREATE OR REPLACE FUNCTION sync_users_table()
            RETURNS TRIGGER AS $$
            BEGIN
                IF TG_OP = 'INSERT' THEN
                    INSERT INTO users (
                        id, password, last_login, is_superuser, first_name, last_name,
                        email, is_staff, is_active, date_joined, anonymous_id,
                        anonymous_id_verified, email_verified, phone_number,
                        phone_number_verified, checkout_phone_number, photo_url,
                        address, created_at, modified_at
                    ) VALUES (
                        NEW.id, NEW.password, NEW.last_login, NEW.is_superuser, NEW.first_name, NEW.last_name,
                        NEW.email, NEW.is_staff, NEW.is_active, NEW.date_joined, NEW.anonymous_id,
                        NEW.anonymous_id_verified, NEW.email_verified, NEW.phone_number,
                        NEW.phone_number_verified, NEW.checkout_phone_number, NEW.photo_url,
                        NEW.address, NEW.created_at, NEW.modified_at
                    );
                    RETURN NEW;
                ELSIF TG_OP = 'UPDATE' THEN
                    UPDATE users SET
                        password = NEW.password,
                        last_login = NEW.last_login,
                        is_superuser = NEW.is_superuser,
                        first_name = NEW.first_name,
                        last_name = NEW.last_name,
                        email = NEW.email,
                        is_staff = NEW.is_staff,
                        is_active = NEW.is_active,
                        date_joined = NEW.date_joined,
                        anonymous_id = NEW.anonymous_id,
                        anonymous_id_verified = NEW.anonymous_id_verified,
                        email_verified = NEW.email_verified,
                        phone_number = NEW.phone_number,
                        phone_number_verified = NEW.phone_number_verified,
                        checkout_phone_number = NEW.checkout_phone_number,
                        photo_url = NEW.photo_url,
                        address = NEW.address,
                        created_at = NEW.created_at,
                        modified_at = NEW.modified_at
                    WHERE id = NEW.id;
                    RETURN NEW;
                ELSIF TG_OP = 'DELETE' THEN
                    DELETE FROM users WHERE id = OLD.id;
                    RETURN OLD;
                END IF;
                RETURN NULL;
            END;
            $$ LANGUAGE plpgsql;
            """,
            reverse_sql="DROP FUNCTION IF EXISTS sync_users_table();",
        ),
        
        # Create triggers to keep users table in sync with authentication_user
        migrations.RunSQL(
            sql="""
            CREATE TRIGGER sync_users_insert
                AFTER INSERT ON authentication_user
                FOR EACH ROW EXECUTE FUNCTION sync_users_table();
                
            CREATE TRIGGER sync_users_update
                AFTER UPDATE ON authentication_user
                FOR EACH ROW EXECUTE FUNCTION sync_users_table();
                
            CREATE TRIGGER sync_users_delete
                AFTER DELETE ON authentication_user
                FOR EACH ROW EXECUTE FUNCTION sync_users_table();
            """,
            reverse_sql="""
            DROP TRIGGER IF EXISTS sync_users_insert ON authentication_user;
            DROP TRIGGER IF EXISTS sync_users_update ON authentication_user;
            DROP TRIGGER IF EXISTS sync_users_delete ON authentication_user;
            """,
        ),
        
        # Populate users table with existing authentication_user data
        migrations.RunSQL(
            sql="""
            INSERT INTO users (
                id, password, last_login, is_superuser, first_name, last_name,
                email, is_staff, is_active, date_joined, anonymous_id,
                anonymous_id_verified, email_verified, phone_number,
                phone_number_verified, checkout_phone_number, photo_url,
                address, created_at, modified_at
            )
            SELECT 
                id, password, last_login, is_superuser, first_name, last_name,
                email, is_staff, is_active, date_joined, anonymous_id,
                anonymous_id_verified, email_verified, phone_number,
                phone_number_verified, checkout_phone_number, photo_url,
                address, created_at, modified_at
            FROM authentication_user
            ON CONFLICT (id) DO NOTHING;
            """,
            reverse_sql="TRUNCATE users;",
        ),
        
        # Add foreign key constraints to listening_events and reviews tables
        migrations.RunSQL(
            sql="""
            -- Add foreign key from listening_events to users
            ALTER TABLE listening_events 
            ADD CONSTRAINT fk_listening_events_user_id 
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
            
            -- Add foreign key from reviews to users  
            ALTER TABLE reviews 
            ADD CONSTRAINT fk_reviews_user_id 
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
            """,
            reverse_sql="""
            ALTER TABLE listening_events DROP CONSTRAINT IF EXISTS fk_listening_events_user_id;
            ALTER TABLE reviews DROP CONSTRAINT IF EXISTS fk_reviews_user_id;
            """,
        ),
    ]