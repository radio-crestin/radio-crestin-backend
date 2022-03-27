CREATE TABLE "public"."station_now_playing" ("id" serial NOT NULL, "created_at" timestamptz NOT NULL DEFAULT now(), "updated_at" timestamptz NOT NULL DEFAULT now(), "timestamp" timestamptz NOT NULL, "station_id" integer NOT NULL, "song_id" integer, "raw_data" jsonb NOT NULL, "error" jsonb, "listeners" integer, PRIMARY KEY ("id") , FOREIGN KEY ("station_id") REFERENCES "public"."station"("id") ON UPDATE set null ON DELETE set null, FOREIGN KEY ("song_id") REFERENCES "public"."song"("id") ON UPDATE restrict ON DELETE restrict);
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
CREATE TRIGGER "set_public_station_now_playing_updated_at"
BEFORE UPDATE ON "public"."station_now_playing"
FOR EACH ROW
EXECUTE PROCEDURE "public"."set_current_timestamp_updated_at"();
COMMENT ON TRIGGER "set_public_station_now_playing_updated_at" ON "public"."station_now_playing" 
IS 'trigger to set value of column "updated_at" to current timestamp on row update';
