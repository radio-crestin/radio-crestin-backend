CREATE FUNCTION radio_crestion_listeners(station_row stations)
RETURNS TEXT AS $$
  SELECT COUNT(*) FROM listening_events WHERE station_id=station_row.id AND timestamp > NOW() - '1 minute'::interval;
$$ LANGUAGE sql STABLE;
