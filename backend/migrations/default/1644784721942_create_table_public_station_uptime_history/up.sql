CREATE TABLE "public"."station_uptime_history" ("id" serial NOT NULL, "created_at" timestamptz NOT NULL DEFAULT now(), "updated_at" timestamptz NOT NULL DEFAULT now(), "timestamp" timestamptz NOT NULL, "station_id" integer NOT NULL, "is_up" boolean NOT NULL, "latency_ms" integer NOT NULL, "rawData" jsonb NOT NULL, PRIMARY KEY ("id") , FOREIGN KEY ("station_id") REFERENCES "public"."station"("id") ON UPDATE cascade ON DELETE cascade);
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
CREATE TRIGGER "set_public_station_uptime_history_updated_at"
BEFORE UPDATE ON "public"."station_uptime_history"
FOR EACH ROW
EXECUTE PROCEDURE "public"."set_current_timestamp_updated_at"();
COMMENT ON TRIGGER "set_public_station_uptime_history_updated_at" ON "public"."station_uptime_history" 
IS 'trigger to set value of column "updated_at" to current timestamp on row update';
