alter table "public"."station" alter column "is_up" drop not null;
alter table "public"."station" add column "is_up" bool;
