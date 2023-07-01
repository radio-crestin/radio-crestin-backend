CREATE OR REPLACE FUNCTION public.stations_total_listeners(station_row stations)
 RETURNS integer
 LANGUAGE sql
 STABLE
AS $function$
SELECT COALESCE(public.radio_crestin_listeners(station_row), 0) + (SELECT listeners FROM stations_now_playing WHERE id = station_row.latest_station_now_playing_id LIMIT 1);
$function$;
