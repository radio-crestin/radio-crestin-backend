alter table "public"."station"
  add constraint "station_latest_station_uptime_id_fkey"
  foreign key ("latest_station_uptime_id")
  references "public"."station_uptime_history"
  ("id") on update restrict on delete restrict;
