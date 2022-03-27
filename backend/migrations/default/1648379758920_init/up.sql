SET check_function_bodies = false;
CREATE TABLE public.stations (
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    "order" integer DEFAULT 0 NOT NULL,
    title text NOT NULL,
    website text NOT NULL,
    email text NOT NULL,
    stream_url text NOT NULL,
    thumbnail_url text NOT NULL,
    latest_station_uptime_id integer,
    latest_station_now_playing_id integer
);
CREATE TABLE public.stations_now_playing (
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    station_id integer,
    song_id integer,
    raw_data jsonb NOT NULL,
    error jsonb,
    listeners integer
);
CREATE FUNCTION public.get_latest_station_now_playing(station public.stations) RETURNS public.stations_now_playing
    LANGUAGE sql STABLE
    AS $$
  SELECT *
  FROM station_now_playing
  WHERE
    station_now_playing.timestamp > NOW() - '3 minutes'::interval AND
    station_now_playing.station_id = station.id
  ORDER BY station_now_playing.timestamp DESC
  LIMIT 1;
$$;
CREATE FUNCTION public.set_current_timestamp_updated_at() RETURNS trigger
    LANGUAGE plpgsql
AS $$
DECLARE
    _new record;
BEGIN
    _new := NEW;
    _new."updated_at" = NOW();
    RETURN _new;
END;
$$;
CREATE FUNCTION public.update_station_latest_station_now_playing_id_field() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    DECLARE active_author BOOLEAN;
    BEGIN
    UPDATE stations SET latest_station_now_playing_id=NEW."id" WHERE id = NEW."station_id";
    RETURN NEW;
END;
$$;
CREATE FUNCTION public.update_station_latest_station_uptime_id_field() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    DECLARE active_author BOOLEAN;
    BEGIN
    UPDATE stations SET latest_station_uptime_id=NEW."id" WHERE id = NEW."station_id";
    RETURN NEW;
END;
$$;
CREATE TABLE public.station_groups (
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    name text NOT NULL,
    "order" numeric DEFAULT '0'::numeric NOT NULL
);
CREATE TABLE public.songs (
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    name text NOT NULL,
    artist text
);
CREATE SEQUENCE public.song_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.song_id_seq OWNED BY public.songs.id;
CREATE SEQUENCE public.station_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.station_id_seq OWNED BY public.stations.id;
CREATE TABLE public.station_metadata_fetch_categories (
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    slug text NOT NULL
);
CREATE SEQUENCE public.station_metadata_fetch_category_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.station_metadata_fetch_category_id_seq OWNED BY public.station_metadata_fetch_categories.id;
CREATE TABLE public.stations_metadata_fetch (
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    station_id integer,
    station_metadata_fetch_category_id integer NOT NULL,
    url text NOT NULL
);
CREATE SEQUENCE public.station_metadata_fetch_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.station_metadata_fetch_id_seq OWNED BY public.stations_metadata_fetch.id;
CREATE SEQUENCE public.station_now_playing_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.station_now_playing_id_seq OWNED BY public.stations_now_playing.id;
CREATE TABLE public.station_to_station_group (
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    station_id integer NOT NULL,
    group_id integer NOT NULL
);
CREATE SEQUENCE public.station_to_group_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
CREATE SEQUENCE public.group_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.group_id_seq OWNED BY public.station_groups.id;
ALTER SEQUENCE public.station_to_group_id_seq OWNED BY public.station_to_station_group.id;
CREATE TABLE public.stations_uptime (
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    station_id integer NOT NULL,
    is_up boolean NOT NULL,
    latency_ms integer NOT NULL,
    raw_data jsonb NOT NULL
);
CREATE SEQUENCE public.station_uptime_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.station_uptime_history_id_seq OWNED BY public.stations_uptime.id;
ALTER TABLE ONLY public.songs ALTER COLUMN id SET DEFAULT nextval('public.song_id_seq'::regclass);
ALTER TABLE ONLY public.station_groups ALTER COLUMN id SET DEFAULT nextval('public.group_id_seq'::regclass);
ALTER TABLE ONLY public.station_metadata_fetch_categories ALTER COLUMN id SET DEFAULT nextval('public.station_metadata_fetch_category_id_seq'::regclass);
ALTER TABLE ONLY public.station_to_station_group ALTER COLUMN id SET DEFAULT nextval('public.station_to_group_id_seq'::regclass);
ALTER TABLE ONLY public.stations ALTER COLUMN id SET DEFAULT nextval('public.station_id_seq'::regclass);
ALTER TABLE ONLY public.stations_metadata_fetch ALTER COLUMN id SET DEFAULT nextval('public.station_metadata_fetch_id_seq'::regclass);
ALTER TABLE ONLY public.stations_now_playing ALTER COLUMN id SET DEFAULT nextval('public.station_now_playing_id_seq'::regclass);
ALTER TABLE ONLY public.stations_uptime ALTER COLUMN id SET DEFAULT nextval('public.station_uptime_history_id_seq'::regclass);
ALTER TABLE ONLY public.station_groups
    ADD CONSTRAINT group_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.songs
    ADD CONSTRAINT song_name_artist_key UNIQUE (name, artist);
ALTER TABLE ONLY public.songs
    ADD CONSTRAINT song_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.station_groups
    ADD CONSTRAINT station_group_name_key UNIQUE (name);
ALTER TABLE ONLY public.station_metadata_fetch_categories
    ADD CONSTRAINT station_metadata_fetch_category_name_key UNIQUE (slug);
ALTER TABLE ONLY public.station_metadata_fetch_categories
    ADD CONSTRAINT station_metadata_fetch_category_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.stations_metadata_fetch
    ADD CONSTRAINT station_metadata_fetch_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.stations_now_playing
    ADD CONSTRAINT station_now_playing_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.stations
    ADD CONSTRAINT station_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.station_to_station_group
    ADD CONSTRAINT station_to_group_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.station_to_station_group
    ADD CONSTRAINT station_to_group_station_id_group_id_key UNIQUE (station_id, group_id);
ALTER TABLE ONLY public.stations_uptime
    ADD CONSTRAINT station_uptime_history_pkey PRIMARY KEY (id);
CREATE INDEX station_now_playing_timestamp ON public.stations_now_playing USING btree ("timestamp");
CREATE INDEX station_uptime_timestamp_idx ON public.stations_uptime USING btree ("timestamp");
CREATE TRIGGER set_public_group_updated_at BEFORE UPDATE ON public.station_groups FOR EACH ROW EXECUTE FUNCTION public.set_current_timestamp_updated_at();
COMMENT ON TRIGGER set_public_group_updated_at ON public.station_groups IS 'trigger to set value of column "updated_at" to current timestamp on row update';
CREATE TRIGGER set_public_song_updated_at BEFORE UPDATE ON public.songs FOR EACH ROW EXECUTE FUNCTION public.set_current_timestamp_updated_at();
COMMENT ON TRIGGER set_public_song_updated_at ON public.songs IS 'trigger to set value of column "updated_at" to current timestamp on row update';
CREATE TRIGGER set_public_station_metadata_fetch_category_updated_at BEFORE UPDATE ON public.station_metadata_fetch_categories FOR EACH ROW EXECUTE FUNCTION public.set_current_timestamp_updated_at();
COMMENT ON TRIGGER set_public_station_metadata_fetch_category_updated_at ON public.station_metadata_fetch_categories IS 'trigger to set value of column "updated_at" to current timestamp on row update';
CREATE TRIGGER set_public_station_metadata_fetch_updated_at BEFORE UPDATE ON public.stations_metadata_fetch FOR EACH ROW EXECUTE FUNCTION public.set_current_timestamp_updated_at();
COMMENT ON TRIGGER set_public_station_metadata_fetch_updated_at ON public.stations_metadata_fetch IS 'trigger to set value of column "updated_at" to current timestamp on row update';
CREATE TRIGGER set_public_station_now_playing_updated_at BEFORE UPDATE ON public.stations_now_playing FOR EACH ROW EXECUTE FUNCTION public.set_current_timestamp_updated_at();
COMMENT ON TRIGGER set_public_station_now_playing_updated_at ON public.stations_now_playing IS 'trigger to set value of column "updated_at" to current timestamp on row update';
CREATE TRIGGER set_public_station_to_group_updated_at BEFORE UPDATE ON public.station_to_station_group FOR EACH ROW EXECUTE FUNCTION public.set_current_timestamp_updated_at();
COMMENT ON TRIGGER set_public_station_to_group_updated_at ON public.station_to_station_group IS 'trigger to set value of column "updated_at" to current timestamp on row update';
CREATE TRIGGER set_public_station_updated_at BEFORE UPDATE ON public.stations FOR EACH ROW EXECUTE FUNCTION public.set_current_timestamp_updated_at();
COMMENT ON TRIGGER set_public_station_updated_at ON public.stations IS 'trigger to set value of column "updated_at" to current timestamp on row update';
CREATE TRIGGER set_public_station_uptime_history_updated_at BEFORE UPDATE ON public.stations_uptime FOR EACH ROW EXECUTE FUNCTION public.set_current_timestamp_updated_at();
COMMENT ON TRIGGER set_public_station_uptime_history_updated_at ON public.stations_uptime IS 'trigger to set value of column "updated_at" to current timestamp on row update';
CREATE TRIGGER update_station_latest_station_now_playing_id_field AFTER INSERT ON public.stations_now_playing FOR EACH ROW EXECUTE FUNCTION public.update_station_latest_station_now_playing_id_field();
CREATE TRIGGER update_station_latest_station_uptime_id_field AFTER INSERT ON public.stations_uptime FOR EACH ROW EXECUTE FUNCTION public.update_station_latest_station_uptime_id_field();
ALTER TABLE ONLY public.stations_metadata_fetch
    ADD CONSTRAINT station_metadata_fetch_station_id_fkey FOREIGN KEY (station_id) REFERENCES public.stations(id) ON UPDATE CASCADE ON DELETE CASCADE;
ALTER TABLE ONLY public.stations_metadata_fetch
    ADD CONSTRAINT station_metadata_fetch_station_metadata_fetch_category_id_fkey FOREIGN KEY (station_metadata_fetch_category_id) REFERENCES public.station_metadata_fetch_categories(id) ON UPDATE RESTRICT ON DELETE RESTRICT;
ALTER TABLE ONLY public.stations_now_playing
    ADD CONSTRAINT station_now_playing_song_id_fkey FOREIGN KEY (song_id) REFERENCES public.songs(id) ON UPDATE RESTRICT ON DELETE RESTRICT;
ALTER TABLE ONLY public.stations_now_playing
    ADD CONSTRAINT station_now_playing_station_id_fkey FOREIGN KEY (station_id) REFERENCES public.stations(id) ON UPDATE SET NULL ON DELETE SET NULL;
ALTER TABLE ONLY public.station_to_station_group
    ADD CONSTRAINT station_to_group_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.station_groups(id) ON UPDATE CASCADE ON DELETE CASCADE;
ALTER TABLE ONLY public.station_to_station_group
    ADD CONSTRAINT station_to_group_station_id_fkey FOREIGN KEY (station_id) REFERENCES public.stations(id) ON UPDATE CASCADE ON DELETE CASCADE;
ALTER TABLE ONLY public.stations_uptime
    ADD CONSTRAINT station_uptime_history_station_id_fkey FOREIGN KEY (station_id) REFERENCES public.stations(id) ON UPDATE CASCADE ON DELETE CASCADE;
ALTER TABLE ONLY public.stations
    ADD CONSTRAINT stations_latest_station_now_playing_id_fkey FOREIGN KEY (latest_station_now_playing_id) REFERENCES public.stations_now_playing(id) ON UPDATE SET NULL ON DELETE SET NULL;
ALTER TABLE ONLY public.stations
    ADD CONSTRAINT stations_latest_station_uptime_id_fkey FOREIGN KEY (latest_station_uptime_id) REFERENCES public.stations_uptime(id) ON UPDATE SET NULL ON DELETE SET NULL;
