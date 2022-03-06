CREATE  INDEX "station_now_playing_timestamp" on
  "public"."station_now_playing" using btree ("timestamp");
