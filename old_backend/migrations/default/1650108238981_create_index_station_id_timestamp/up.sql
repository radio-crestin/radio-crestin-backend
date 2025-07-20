CREATE  INDEX "station_id_timestamp" on
  "public"."listening_events" using btree ("station_id", "timestamp");
