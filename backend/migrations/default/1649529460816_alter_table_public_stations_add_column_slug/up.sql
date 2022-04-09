alter table "public"."stations" add column "slug" text
 null;
UPDATE stations SET slug=REPLACE(LOWER(title), ' ', '-');
alter table "public"."stations" alter column "slug" set not null;
alter table "public"."stations" add constraint "stations_slug_key" unique ("slug");

