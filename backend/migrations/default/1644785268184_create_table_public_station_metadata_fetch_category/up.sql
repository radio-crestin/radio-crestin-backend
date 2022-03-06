CREATE TABLE "public"."station_metadata_fetch_category" ("id" serial NOT NULL, "created_at" timestamptz NOT NULL DEFAULT now(), "updated_at" timestamptz NOT NULL DEFAULT now(), "name" text NOT NULL, PRIMARY KEY ("id") , UNIQUE ("name"));
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
CREATE TRIGGER "set_public_station_metadata_fetch_category_updated_at"
BEFORE UPDATE ON "public"."station_metadata_fetch_category"
FOR EACH ROW
EXECUTE PROCEDURE "public"."set_current_timestamp_updated_at"();
COMMENT ON TRIGGER "set_public_station_metadata_fetch_category_updated_at" ON "public"."station_metadata_fetch_category" 
IS 'trigger to set value of column "updated_at" to current timestamp on row update';
