alter table "public"."reviews"
  add constraint "reviews_user_id_fkey"
  foreign key ("user_id")
  references "public"."users"
  ("id") on update set null on delete set null;
