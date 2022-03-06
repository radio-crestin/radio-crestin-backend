alter table "public"."stations" drop constraint "station_latest_station_now_playing_id_fkey",
  add constraint "stations_latest_station_now_playing_id_fkey"
  foreign key ("latest_station_now_playing_id")
  references "public"."stations_now_playing"
  ("id") on update cascade on delete cascade;
