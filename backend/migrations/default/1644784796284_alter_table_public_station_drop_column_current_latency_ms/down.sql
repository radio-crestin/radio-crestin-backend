alter table "public"."station" alter column "current_latency_ms" drop not null;
alter table "public"."station" add column "current_latency_ms" int4;
