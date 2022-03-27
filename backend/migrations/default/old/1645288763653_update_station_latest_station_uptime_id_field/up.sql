CREATE OR REPLACE FUNCTION update_station_latest_station_uptime_id_field()
    RETURNS trigger AS $BODY$
    DECLARE active_author BOOLEAN;
    BEGIN
    UPDATE stations SET latest_station_uptime_id=NEW."id" WHERE id = NEW."station_id";
    RETURN NEW;
END;
$BODY$ LANGUAGE plpgsql;
