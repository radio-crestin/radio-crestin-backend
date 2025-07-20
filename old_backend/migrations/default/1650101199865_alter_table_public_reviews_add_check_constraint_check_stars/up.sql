alter table "public"."reviews" add constraint "check_stars" check (stars >= 0 and stars <= 5);
