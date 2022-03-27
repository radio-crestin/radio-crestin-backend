CREATE TABLE "public"."station" ("id" serial NOT NULL, "created_at" timestamptz NOT NULL DEFAULT now(), "updated_at" timestamptz NOT NULL DEFAULT now(), "order" integer NOT NULL DEFAULT 0, "title" text NOT NULL, "website" text NOT NULL, "email" text NOT NULL, "streamUrl" text NOT NULL, "thumbnailUrl" text NOT NULL, PRIMARY KEY ("id") );
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
CREATE TRIGGER "set_public_station_updated_at"
BEFORE UPDATE ON "public"."station"
FOR EACH ROW
EXECUTE PROCEDURE "public"."set_current_timestamp_updated_at"();
COMMENT ON TRIGGER "set_public_station_updated_at" ON "public"."station" 
IS 'trigger to set value of column "updated_at" to current timestamp on row update';
