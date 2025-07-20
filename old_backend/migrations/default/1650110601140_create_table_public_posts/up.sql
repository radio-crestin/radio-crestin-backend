CREATE TABLE "public"."posts" ("id" serial NOT NULL, "created_at" timestamptz NOT NULL DEFAULT now(), "updated_at" timestamptz NOT NULL DEFAULT now(), "station_id" integer NOT NULL, "title" text NOT NULL, "link" text NOT NULL, "description" text NOT NULL, "published" timestamptz NOT NULL, PRIMARY KEY ("id") , FOREIGN KEY ("station_id") REFERENCES "public"."stations"("id") ON UPDATE cascade ON DELETE cascade, UNIQUE ("station_id", "link"));
CREATE OR REPLACE FUNCTION "public"."set_current_timestamp_updated_at"()
RETURNS TRIGGER AS $$
DECLARE
  _new record;
BEGIN
  _new := NEW;
  _new."updated_at" = NOW();
  RETURN _new;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER "set_public_posts_updated_at"
BEFORE UPDATE ON "public"."posts"
FOR EACH ROW
EXECUTE PROCEDURE "public"."set_current_timestamp_updated_at"();
COMMENT ON TRIGGER "set_public_posts_updated_at" ON "public"."posts" 
IS 'trigger to set value of column "updated_at" to current timestamp on row update';
