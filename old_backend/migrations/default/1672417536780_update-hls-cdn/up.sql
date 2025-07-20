DROP FUNCTION IF EXISTS hls_stream_url(station_row stations);
CREATE FUNCTION hls_stream_url(station_row stations)
RETURNS TEXT AS $$
  SELECT 'https://cf-hls.radio-crestin.com/hls/' || station_row.slug || '/index.m3u8';
$$ LANGUAGE sql STABLE;
