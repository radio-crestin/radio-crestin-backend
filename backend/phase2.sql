-- Phase 2: Additional database setup and permissions

-- Add info column to listening_events if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='listening_events' AND column_name='info'
    ) THEN
        ALTER TABLE listening_events ADD COLUMN info jsonb;
    END IF;
END $$;

-- Grant necessary permissions for computed functions
GRANT USAGE ON SCHEMA public TO postgres;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO postgres;

-- Create indexes for better performance on listening_events
CREATE INDEX IF NOT EXISTS idx_listening_events_station_id ON listening_events(station_id);
CREATE INDEX IF NOT EXISTS idx_listening_events_user_id ON listening_events(user_id);
CREATE INDEX IF NOT EXISTS idx_listening_events_created_at ON listening_events(created_at);

-- Ensure authentication_user table permissions
GRANT SELECT ON authentication_user TO postgres;

-- Comment on the users view
COMMENT ON VIEW users IS 'View that aliases authentication_user table for Hasura compatibility';