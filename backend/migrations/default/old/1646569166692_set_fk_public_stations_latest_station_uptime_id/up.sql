alter table "public"."stations" drop constraint "stations_latest_station_uptime_id_fkey",
  add constraint "stations_latest_station_uptime_id_fkey"
  foreign key ("latest_station_uptime_id")
  references "public"."stations_uptime"
  ("id") on update set null on delete set null;
