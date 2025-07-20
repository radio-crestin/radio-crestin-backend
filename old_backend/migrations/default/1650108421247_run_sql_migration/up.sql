DROP FUNCTION IF EXISTS radio_crestion_listeners(station_row stations);
CREATE FUNCTION radio_crestion_listeners(station_row stations)
RETURNS INT AS $$
  SELECT COUNT(user_id) FROM listening_events WHERE station_id=station_row.id AND timestamp > NOW() - '1 minute'::interval GROUP BY user_id;
$$ LANGUAGE sql STABLE;