alter table "public"."station" alter column "current_song_id" drop not null;
alter table "public"."station" add column "current_song_id" int4;
