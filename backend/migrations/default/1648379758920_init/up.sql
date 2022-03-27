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
CREATE TABLE public.auth_group (
    id integer NOT NULL,
    name character varying(150) NOT NULL
);
CREATE SEQUENCE public.auth_group_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.auth_group_id_seq OWNED BY public.auth_group.id;
CREATE TABLE public.auth_group_permissions (
    id bigint NOT NULL,
    group_id integer NOT NULL,
    permission_id integer NOT NULL
);
CREATE SEQUENCE public.auth_group_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.auth_group_permissions_id_seq OWNED BY public.auth_group_permissions.id;
CREATE TABLE public.auth_permission (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    content_type_id integer NOT NULL,
    codename character varying(100) NOT NULL
);
CREATE SEQUENCE public.auth_permission_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.auth_permission_id_seq OWNED BY public.auth_permission.id;
CREATE TABLE public.auth_user (
    id integer NOT NULL,
    password character varying(128) NOT NULL,
    last_login timestamp with time zone,
    is_superuser boolean NOT NULL,
    username character varying(150) NOT NULL,
    first_name character varying(150) NOT NULL,
    last_name character varying(150) NOT NULL,
    email character varying(254) NOT NULL,
    is_staff boolean NOT NULL,
    is_active boolean NOT NULL,
    date_joined timestamp with time zone NOT NULL
);
CREATE TABLE public.auth_user_groups (
    id bigint NOT NULL,
    user_id integer NOT NULL,
    group_id integer NOT NULL
);
CREATE SEQUENCE public.auth_user_groups_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.auth_user_groups_id_seq OWNED BY public.auth_user_groups.id;
CREATE SEQUENCE public.auth_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.auth_user_id_seq OWNED BY public.auth_user.id;
CREATE TABLE public.auth_user_user_permissions (
    id bigint NOT NULL,
    user_id integer NOT NULL,
    permission_id integer NOT NULL
);
CREATE SEQUENCE public.auth_user_user_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.auth_user_user_permissions_id_seq OWNED BY public.auth_user_user_permissions.id;
CREATE TABLE public.django_admin_log (
    id integer NOT NULL,
    action_time timestamp with time zone NOT NULL,
    object_id text,
    object_repr character varying(200) NOT NULL,
    action_flag smallint NOT NULL,
    change_message text NOT NULL,
    content_type_id integer,
    user_id integer NOT NULL,
    CONSTRAINT django_admin_log_action_flag_check CHECK ((action_flag >= 0))
);
CREATE SEQUENCE public.django_admin_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.django_admin_log_id_seq OWNED BY public.django_admin_log.id;
CREATE TABLE public.django_content_type (
    id integer NOT NULL,
    app_label character varying(100) NOT NULL,
    model character varying(100) NOT NULL
);
CREATE SEQUENCE public.django_content_type_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.django_content_type_id_seq OWNED BY public.django_content_type.id;
CREATE TABLE public.django_migrations (
    id bigint NOT NULL,
    app character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    applied timestamp with time zone NOT NULL
);
CREATE SEQUENCE public.django_migrations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.django_migrations_id_seq OWNED BY public.django_migrations.id;
CREATE TABLE public.django_session (
    session_key character varying(40) NOT NULL,
    session_data text NOT NULL,
    expire_date timestamp with time zone NOT NULL
);
CREATE TABLE public.station_groups (
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    name text NOT NULL,
    "order" numeric DEFAULT '0'::numeric NOT NULL
);
CREATE SEQUENCE public.group_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.group_id_seq OWNED BY public.station_groups.id;
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
ALTER TABLE ONLY public.auth_group ALTER COLUMN id SET DEFAULT nextval('public.auth_group_id_seq'::regclass);
ALTER TABLE ONLY public.auth_group_permissions ALTER COLUMN id SET DEFAULT nextval('public.auth_group_permissions_id_seq'::regclass);
ALTER TABLE ONLY public.auth_permission ALTER COLUMN id SET DEFAULT nextval('public.auth_permission_id_seq'::regclass);
ALTER TABLE ONLY public.auth_user ALTER COLUMN id SET DEFAULT nextval('public.auth_user_id_seq'::regclass);
ALTER TABLE ONLY public.auth_user_groups ALTER COLUMN id SET DEFAULT nextval('public.auth_user_groups_id_seq'::regclass);
ALTER TABLE ONLY public.auth_user_user_permissions ALTER COLUMN id SET DEFAULT nextval('public.auth_user_user_permissions_id_seq'::regclass);
ALTER TABLE ONLY public.django_admin_log ALTER COLUMN id SET DEFAULT nextval('public.django_admin_log_id_seq'::regclass);
ALTER TABLE ONLY public.django_content_type ALTER COLUMN id SET DEFAULT nextval('public.django_content_type_id_seq'::regclass);
ALTER TABLE ONLY public.django_migrations ALTER COLUMN id SET DEFAULT nextval('public.django_migrations_id_seq'::regclass);
ALTER TABLE ONLY public.songs ALTER COLUMN id SET DEFAULT nextval('public.song_id_seq'::regclass);
ALTER TABLE ONLY public.station_groups ALTER COLUMN id SET DEFAULT nextval('public.group_id_seq'::regclass);
ALTER TABLE ONLY public.station_metadata_fetch_categories ALTER COLUMN id SET DEFAULT nextval('public.station_metadata_fetch_category_id_seq'::regclass);
ALTER TABLE ONLY public.station_to_station_group ALTER COLUMN id SET DEFAULT nextval('public.station_to_group_id_seq'::regclass);
ALTER TABLE ONLY public.stations ALTER COLUMN id SET DEFAULT nextval('public.station_id_seq'::regclass);
ALTER TABLE ONLY public.stations_metadata_fetch ALTER COLUMN id SET DEFAULT nextval('public.station_metadata_fetch_id_seq'::regclass);
ALTER TABLE ONLY public.stations_now_playing ALTER COLUMN id SET DEFAULT nextval('public.station_now_playing_id_seq'::regclass);
ALTER TABLE ONLY public.stations_uptime ALTER COLUMN id SET DEFAULT nextval('public.station_uptime_history_id_seq'::regclass);
ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_name_key UNIQUE (name);
ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_permission_id_0cd325b0_uniq UNIQUE (group_id, permission_id);
ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_codename_01ab375a_uniq UNIQUE (content_type_id, codename);
ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_user_id_group_id_94350c0c_uniq UNIQUE (user_id, group_id);
ALTER TABLE ONLY public.auth_user
    ADD CONSTRAINT auth_user_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_user_id_permission_id_14a6b632_uniq UNIQUE (user_id, permission_id);
ALTER TABLE ONLY public.auth_user
    ADD CONSTRAINT auth_user_username_key UNIQUE (username);
ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_app_label_model_76bd3d3b_uniq UNIQUE (app_label, model);
ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.django_migrations
    ADD CONSTRAINT django_migrations_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.django_session
    ADD CONSTRAINT django_session_pkey PRIMARY KEY (session_key);
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
CREATE INDEX auth_group_name_a6ea08ec_like ON public.auth_group USING btree (name varchar_pattern_ops);
CREATE INDEX auth_group_permissions_group_id_b120cbf9 ON public.auth_group_permissions USING btree (group_id);
CREATE INDEX auth_group_permissions_permission_id_84c5c92e ON public.auth_group_permissions USING btree (permission_id);
CREATE INDEX auth_permission_content_type_id_2f476e4b ON public.auth_permission USING btree (content_type_id);
CREATE INDEX auth_user_groups_group_id_97559544 ON public.auth_user_groups USING btree (group_id);
CREATE INDEX auth_user_groups_user_id_6a12ed8b ON public.auth_user_groups USING btree (user_id);
CREATE INDEX auth_user_user_permissions_permission_id_1fbb5f2c ON public.auth_user_user_permissions USING btree (permission_id);
CREATE INDEX auth_user_user_permissions_user_id_a95ead1b ON public.auth_user_user_permissions USING btree (user_id);
CREATE INDEX auth_user_username_6821ab7c_like ON public.auth_user USING btree (username varchar_pattern_ops);
CREATE INDEX django_admin_log_content_type_id_c4bce8eb ON public.django_admin_log USING btree (content_type_id);
CREATE INDEX django_admin_log_user_id_c564eba6 ON public.django_admin_log USING btree (user_id);
CREATE INDEX django_session_expire_date_a5c62663 ON public.django_session USING btree (expire_date);
CREATE INDEX django_session_session_key_c0390e0f_like ON public.django_session USING btree (session_key varchar_pattern_ops);
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
ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissio_permission_id_84c5c92e_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_b120cbf9_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_2f476e4b_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_group_id_97559544_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_user_id_6a12ed8b_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_content_type_id_c4bce8eb_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_user_id_c564eba6_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;
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
