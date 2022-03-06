alter table "public"."song" add constraint "song_name_artist_key" unique ("name", "artist");
