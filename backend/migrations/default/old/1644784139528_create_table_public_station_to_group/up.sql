CREATE TABLE "public"."station_to_group" ("id" serial NOT NULL, "created_at" timestamptz NOT NULL DEFAULT now(), "updated_at" timestamptz NOT NULL DEFAULT now(), "station_id" integer NOT NULL, "group_id" integer NOT NULL, PRIMARY KEY ("id") , FOREIGN KEY ("station_id") REFERENCES "public"."station"("id") ON UPDATE cascade ON DELETE cascade, FOREIGN KEY ("group_id") REFERENCES "public"."group"("id") ON UPDATE cascade ON DELETE cascade, UNIQUE ("station_id", "group_id"));
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
CREATE TRIGGER "set_public_station_to_group_updated_at"
BEFORE UPDATE ON "public"."station_to_group"
FOR EACH ROW
EXECUTE PROCEDURE "public"."set_current_timestamp_updated_at"();
COMMENT ON TRIGGER "set_public_station_to_group_updated_at" ON "public"."station_to_group" 
IS 'trigger to set value of column "updated_at" to current timestamp on row update';
