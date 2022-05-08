CREATE UNIQUE INDEX "station_group_slug_key" on
  "public"."station_groups" using btree ("slug");
