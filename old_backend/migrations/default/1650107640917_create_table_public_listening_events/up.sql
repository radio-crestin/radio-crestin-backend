CREATE TABLE "public"."listening_events" ("id" serial NOT NULL, "created_at" timestamptz NOT NULL DEFAULT now(), "updated_at" timestamptz NOT NULL DEFAULT now(), "timestamp" timestamptz NOT NULL DEFAULT now(), "user_id" integer NOT NULL, "station_id" integer NOT NULL, "info" jsonb NOT NULL DEFAULT jsonb_build_object(), PRIMARY KEY ("id") , FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON UPDATE cascade ON DELETE cascade, FOREIGN KEY ("station_id") REFERENCES "public"."stations"("id") ON UPDATE cascade ON DELETE cascade);
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
CREATE TRIGGER "set_public_listening_events_updated_at"
BEFORE UPDATE ON "public"."listening_events"
FOR EACH ROW
EXECUTE PROCEDURE "public"."set_current_timestamp_updated_at"();
COMMENT ON TRIGGER "set_public_listening_events_updated_at" ON "public"."listening_events" 
IS 'trigger to set value of column "updated_at" to current timestamp on row update';
