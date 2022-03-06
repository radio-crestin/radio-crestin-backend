alter table "public"."station"
  add constraint "station_latest_station_now_playing_id_fkey"
  foreign key ("latest_station_now_playing_id")
  references "public"."station_now_playing"
  ("id") on update restrict on delete restrict;
