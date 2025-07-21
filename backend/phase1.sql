-- Phase 1: Create users view/table alias for Hasura compatibility
-- This creates a "users" table as a view referencing authentication_user

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

-- Create computed functions for stations table

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

-- Function to generate proxy stream URL
CREATE OR REPLACE FUNCTION proxy_stream_url(stations_row stations)
RETURNS text AS $$
BEGIN
    RETURN '/api/stream/proxy/' || stations_row.id || '/';
END;
$$ LANGUAGE plpgsql STABLE;

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