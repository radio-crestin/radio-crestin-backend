CREATE TABLE "public"."station_streams" ("id" serial NOT NULL, "created_at" timestamptz NOT NULL DEFAULT now(), "updated_at" timestamptz NOT NULL DEFAULT now(), "station_id" integer NOT NULL, "stream" text NOT NULL, "order" integer NOT NULL DEFAULT 0, PRIMARY KEY ("id") , FOREIGN KEY ("station_id") REFERENCES "public"."stations"("id") ON UPDATE cascade ON DELETE cascade);
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
CREATE TRIGGER "set_public_station_streams_updated_at"
BEFORE UPDATE ON "public"."station_streams"
FOR EACH ROW
EXECUTE PROCEDURE "public"."set_current_timestamp_updated_at"();
COMMENT ON TRIGGER "set_public_station_streams_updated_at" ON "public"."station_streams"
IS 'trigger to set value of column "updated_at" to current timestamp on row update';
