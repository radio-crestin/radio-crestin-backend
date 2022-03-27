alter table "public"."station" alter column "current_listeners" drop not null;
alter table "public"."station" add column "current_listeners" int4;
