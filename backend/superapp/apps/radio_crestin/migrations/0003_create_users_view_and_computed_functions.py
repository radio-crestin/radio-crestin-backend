from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('radio_crestin', '0002_listeningevents_info'),
    ]

    operations = [
        # Create users view for Hasura compatibility
        migrations.RunSQL(
            sql="""
            CREATE OR REPLACE VIEW users AS 
            SELECT 
                id,
                password,
                last_login,
                is_superuser,
                first_name,
                last_name,
                email,
                is_staff,
                is_active,
                date_joined,
                anonymous_id,
                anonymous_id_verified,
                email_verified,
                phone_number,
                phone_number_verified,
                checkout_phone_number,
                photo_url,
                address,
                created_at,
                modified_at
            FROM authentication_user;
            """,
            reverse_sql="DROP VIEW IF EXISTS users;",
        ),
        
        # Create computed functions for stations table
        migrations.RunSQL(
            sql="""
            -- Function to get radio crestin listeners count
            CREATE OR REPLACE FUNCTION radio_crestin_listeners(stations_row stations)
            RETURNS bigint AS $$
            BEGIN
                RETURN (
                    SELECT COUNT(DISTINCT le.user_id)
                    FROM listening_events le
                    WHERE le.station_id = stations_row.id
                    AND le.created_at >= NOW() - INTERVAL '30 days'
                );
            END;
            $$ LANGUAGE plpgsql STABLE;
            """,
            reverse_sql="DROP FUNCTION IF EXISTS radio_crestin_listeners(stations);",
        ),
        
        migrations.RunSQL(
            sql="""
            -- Function to get total listeners for a station
            CREATE OR REPLACE FUNCTION stations_total_listeners(stations_row stations)
            RETURNS bigint AS $$
            BEGIN
                RETURN (
                    SELECT COUNT(DISTINCT le.user_id)
                    FROM listening_events le
                    WHERE le.station_id = stations_row.id
                );
            END;
            $$ LANGUAGE plpgsql STABLE;
            """,
            reverse_sql="DROP FUNCTION IF EXISTS stations_total_listeners(stations);",
        ),
        
        migrations.RunSQL(
            sql="""
            -- Function to generate proxy stream URL
            CREATE OR REPLACE FUNCTION proxy_stream_url(stations_row stations)
            RETURNS text AS $$
            BEGIN
                RETURN '/api/stream/proxy/' || stations_row.id || '/';
            END;
            $$ LANGUAGE plpgsql STABLE;
            """,
            reverse_sql="DROP FUNCTION IF EXISTS proxy_stream_url(stations);",
        ),
        
        migrations.RunSQL(
            sql="""
            -- Function to generate HLS stream URL
            CREATE OR REPLACE FUNCTION hls_stream_url(stations_row stations)
            RETURNS text AS $$
            BEGIN
                RETURN CASE 
                    WHEN stations_row.generate_hls_stream = true 
                    THEN '/api/stream/hls/' || stations_row.id || '/playlist.m3u8'
                    ELSE NULL
                END;
            END;
            $$ LANGUAGE plpgsql STABLE;
            """,
            reverse_sql="DROP FUNCTION IF EXISTS hls_stream_url(stations);",
        ),
        
        # Create indexes for better performance
        migrations.RunSQL(
            sql="""
            CREATE INDEX IF NOT EXISTS idx_listening_events_station_id ON listening_events(station_id);
            CREATE INDEX IF NOT EXISTS idx_listening_events_user_id ON listening_events(user_id);
            CREATE INDEX IF NOT EXISTS idx_listening_events_created_at ON listening_events(created_at);
            """,
            reverse_sql="""
            DROP INDEX IF EXISTS idx_listening_events_station_id;
            DROP INDEX IF EXISTS idx_listening_events_user_id;
            DROP INDEX IF EXISTS idx_listening_events_created_at;
            """,
        ),
        
        # Add comment on the users view
        migrations.RunSQL(
            sql="COMMENT ON VIEW users IS 'View that aliases authentication_user table for Hasura compatibility';",
            reverse_sql="",
        ),
    ]