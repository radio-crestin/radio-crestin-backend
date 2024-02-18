alter table "public"."stations" add column "generate_hls_stream" boolean
 not null default 'true';
