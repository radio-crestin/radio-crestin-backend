DROP FUNCTION IF EXISTS proxy_stream_url(station_row stations);
CREATE FUNCTION proxy_stream_url(station_row stations)
RETURNS TEXT AS $$
  SELECT 'https://proxy.radio-crestin.com/' || station_row.stream_url;
$$ LANGUAGE sql STABLE;
DROP FUNCTION IF EXISTS hls_stream_url(station_row stations);
CREATE FUNCTION hls_stream_url(station_row stations)
RETURNS TEXT AS $$
  SELECT 'https://hls.radio-crestin.com/hls/' || station_row.slug || '/index.m3u8';
$$ LANGUAGE sql STABLE;
