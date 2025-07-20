alter table "public"."reviews" drop constraint "reviews_user_id_fkey",
  add constraint "reviews_user_id_fkey"
  foreign key ("user_id")
  references "public"."users"
  ("id") on update cascade on delete cascade;
