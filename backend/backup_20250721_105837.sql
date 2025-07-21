--
-- PostgreSQL database dump
--

-- Dumped from database version 16.9 (Ubuntu 16.9-1.pgdg22.04+1)
-- Dumped by pg_dump version 16.9 (Ubuntu 16.9-1.pgdg22.04+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: timescaledb; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS timescaledb WITH SCHEMA public;


--
-- Name: EXTENSION timescaledb; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION timescaledb IS 'Enables scalable inserts and complex queries for time-series data (Community Edition)';


--
-- Name: hdb_catalog; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA hdb_catalog;


ALTER SCHEMA hdb_catalog OWNER TO postgres;

--
-- Name: timescaledb_toolkit; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS timescaledb_toolkit WITH SCHEMA public;


--
-- Name: EXTENSION timescaledb_toolkit; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION timescaledb_toolkit IS 'Library of analytical hyperfunctions, time-series pipelining, and other SQL utilities';


--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: gen_hasura_uuid(); Type: FUNCTION; Schema: hdb_catalog; Owner: postgres
--

CREATE FUNCTION hdb_catalog.gen_hasura_uuid() RETURNS uuid
    LANGUAGE sql
    AS $$select gen_random_uuid()$$;


ALTER FUNCTION hdb_catalog.gen_hasura_uuid() OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: stations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.stations (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    disabled boolean NOT NULL,
    "order" double precision NOT NULL,
    slug character varying(50) NOT NULL,
    title text NOT NULL,
    website character varying(200) NOT NULL,
    email text,
    generate_hls_stream boolean NOT NULL,
    stream_url character varying(200) NOT NULL,
    thumbnail character varying(100),
    thumbnail_url character varying(200),
    description text,
    description_action_title text,
    description_link character varying(200),
    rss_feed character varying(200),
    feature_latest_post boolean,
    facebook_page_id text,
    latest_station_now_playing_id bigint,
    latest_station_uptime_id bigint
);


ALTER TABLE public.stations OWNER TO postgres;

--
-- Name: hls_stream_url(public.stations); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.hls_stream_url(stations_row public.stations) RETURNS text
    LANGUAGE plpgsql STABLE
    AS $$
            BEGIN
                RETURN CASE 
                    WHEN stations_row.generate_hls_stream = true 
                    THEN '/api/stream/hls/' || stations_row.id || '/playlist.m3u8'
                    ELSE NULL
                END;
            END;
            $$;


ALTER FUNCTION public.hls_stream_url(stations_row public.stations) OWNER TO postgres;

--
-- Name: proxy_stream_url(public.stations); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.proxy_stream_url(stations_row public.stations) RETURNS text
    LANGUAGE plpgsql STABLE
    AS $$
            BEGIN
                RETURN '/api/stream/proxy/' || stations_row.id || '/';
            END;
            $$;


ALTER FUNCTION public.proxy_stream_url(stations_row public.stations) OWNER TO postgres;

--
-- Name: radio_crestin_listeners(public.stations); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.radio_crestin_listeners(stations_row public.stations) RETURNS bigint
    LANGUAGE plpgsql STABLE
    AS $$
            BEGIN
                RETURN (
                    SELECT COUNT(DISTINCT le.user_id)
                    FROM listening_events le
                    WHERE le.station_id = stations_row.id
                    AND le.created_at >= NOW() - INTERVAL '30 days'
                );
            END;
            $$;


ALTER FUNCTION public.radio_crestin_listeners(stations_row public.stations) OWNER TO postgres;

--
-- Name: stations_total_listeners(public.stations); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.stations_total_listeners(stations_row public.stations) RETURNS bigint
    LANGUAGE plpgsql STABLE
    AS $$
            BEGIN
                RETURN (
                    SELECT COUNT(DISTINCT le.user_id)
                    FROM listening_events le
                    WHERE le.station_id = stations_row.id
                );
            END;
            $$;


ALTER FUNCTION public.stations_total_listeners(stations_row public.stations) OWNER TO postgres;

--
-- Name: sync_users_table(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.sync_users_table() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
            BEGIN
                IF TG_OP = 'INSERT' THEN
                    INSERT INTO users (
                        id, password, last_login, is_superuser, first_name, last_name,
                        email, is_staff, is_active, date_joined, anonymous_id,
                        anonymous_id_verified, email_verified, phone_number,
                        phone_number_verified, checkout_phone_number, photo_url,
                        address, created_at, modified_at
                    ) VALUES (
                        NEW.id, NEW.password, NEW.last_login, NEW.is_superuser, NEW.first_name, NEW.last_name,
                        NEW.email, NEW.is_staff, NEW.is_active, NEW.date_joined, NEW.anonymous_id,
                        NEW.anonymous_id_verified, NEW.email_verified, NEW.phone_number,
                        NEW.phone_number_verified, NEW.checkout_phone_number, NEW.photo_url,
                        NEW.address, NEW.created_at, NEW.modified_at
                    );
                    RETURN NEW;
                ELSIF TG_OP = 'UPDATE' THEN
                    UPDATE users SET
                        password = NEW.password,
                        last_login = NEW.last_login,
                        is_superuser = NEW.is_superuser,
                        first_name = NEW.first_name,
                        last_name = NEW.last_name,
                        email = NEW.email,
                        is_staff = NEW.is_staff,
                        is_active = NEW.is_active,
                        date_joined = NEW.date_joined,
                        anonymous_id = NEW.anonymous_id,
                        anonymous_id_verified = NEW.anonymous_id_verified,
                        email_verified = NEW.email_verified,
                        phone_number = NEW.phone_number,
                        phone_number_verified = NEW.phone_number_verified,
                        checkout_phone_number = NEW.checkout_phone_number,
                        photo_url = NEW.photo_url,
                        address = NEW.address,
                        created_at = NEW.created_at,
                        modified_at = NEW.modified_at
                    WHERE id = NEW.id;
                    RETURN NEW;
                ELSIF TG_OP = 'DELETE' THEN
                    DELETE FROM users WHERE id = OLD.id;
                    RETURN OLD;
                END IF;
                RETURN NULL;
            END;
            $$;


ALTER FUNCTION public.sync_users_table() OWNER TO postgres;

--
-- Name: hdb_action_log; Type: TABLE; Schema: hdb_catalog; Owner: postgres
--

CREATE TABLE hdb_catalog.hdb_action_log (
    id uuid DEFAULT hdb_catalog.gen_hasura_uuid() NOT NULL,
    action_name text,
    input_payload jsonb NOT NULL,
    request_headers jsonb NOT NULL,
    session_variables jsonb NOT NULL,
    response_payload jsonb,
    errors jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    response_received_at timestamp with time zone,
    status text NOT NULL,
    CONSTRAINT hdb_action_log_status_check CHECK ((status = ANY (ARRAY['created'::text, 'processing'::text, 'completed'::text, 'error'::text])))
);


ALTER TABLE hdb_catalog.hdb_action_log OWNER TO postgres;

--
-- Name: hdb_cron_event_invocation_logs; Type: TABLE; Schema: hdb_catalog; Owner: postgres
--

CREATE TABLE hdb_catalog.hdb_cron_event_invocation_logs (
    id text DEFAULT hdb_catalog.gen_hasura_uuid() NOT NULL,
    event_id text,
    status integer,
    request json,
    response json,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE hdb_catalog.hdb_cron_event_invocation_logs OWNER TO postgres;

--
-- Name: hdb_cron_events; Type: TABLE; Schema: hdb_catalog; Owner: postgres
--

CREATE TABLE hdb_catalog.hdb_cron_events (
    id text DEFAULT hdb_catalog.gen_hasura_uuid() NOT NULL,
    trigger_name text NOT NULL,
    scheduled_time timestamp with time zone NOT NULL,
    status text DEFAULT 'scheduled'::text NOT NULL,
    tries integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    next_retry_at timestamp with time zone,
    CONSTRAINT valid_status CHECK ((status = ANY (ARRAY['scheduled'::text, 'locked'::text, 'delivered'::text, 'error'::text, 'dead'::text])))
);


ALTER TABLE hdb_catalog.hdb_cron_events OWNER TO postgres;

--
-- Name: hdb_metadata; Type: TABLE; Schema: hdb_catalog; Owner: postgres
--

CREATE TABLE hdb_catalog.hdb_metadata (
    id integer NOT NULL,
    metadata json NOT NULL,
    resource_version integer DEFAULT 1 NOT NULL
);


ALTER TABLE hdb_catalog.hdb_metadata OWNER TO postgres;

--
-- Name: hdb_scheduled_event_invocation_logs; Type: TABLE; Schema: hdb_catalog; Owner: postgres
--

CREATE TABLE hdb_catalog.hdb_scheduled_event_invocation_logs (
    id text DEFAULT hdb_catalog.gen_hasura_uuid() NOT NULL,
    event_id text,
    status integer,
    request json,
    response json,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE hdb_catalog.hdb_scheduled_event_invocation_logs OWNER TO postgres;

--
-- Name: hdb_scheduled_events; Type: TABLE; Schema: hdb_catalog; Owner: postgres
--

CREATE TABLE hdb_catalog.hdb_scheduled_events (
    id text DEFAULT hdb_catalog.gen_hasura_uuid() NOT NULL,
    webhook_conf json NOT NULL,
    scheduled_time timestamp with time zone NOT NULL,
    retry_conf json,
    payload json,
    header_conf json,
    status text DEFAULT 'scheduled'::text NOT NULL,
    tries integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    next_retry_at timestamp with time zone,
    comment text,
    CONSTRAINT valid_status CHECK ((status = ANY (ARRAY['scheduled'::text, 'locked'::text, 'delivered'::text, 'error'::text, 'dead'::text])))
);


ALTER TABLE hdb_catalog.hdb_scheduled_events OWNER TO postgres;

--
-- Name: hdb_schema_notifications; Type: TABLE; Schema: hdb_catalog; Owner: postgres
--

CREATE TABLE hdb_catalog.hdb_schema_notifications (
    id integer NOT NULL,
    notification json NOT NULL,
    resource_version integer DEFAULT 1 NOT NULL,
    instance_id uuid NOT NULL,
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT hdb_schema_notifications_id_check CHECK ((id = 1))
);


ALTER TABLE hdb_catalog.hdb_schema_notifications OWNER TO postgres;

--
-- Name: hdb_version; Type: TABLE; Schema: hdb_catalog; Owner: postgres
--

CREATE TABLE hdb_catalog.hdb_version (
    hasura_uuid uuid DEFAULT hdb_catalog.gen_hasura_uuid() NOT NULL,
    version text NOT NULL,
    upgraded_on timestamp with time zone NOT NULL,
    cli_state jsonb DEFAULT '{}'::jsonb NOT NULL,
    console_state jsonb DEFAULT '{}'::jsonb NOT NULL,
    ee_client_id text,
    ee_client_secret text
);


ALTER TABLE hdb_catalog.hdb_version OWNER TO postgres;

--
-- Name: account_emailaddress; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.account_emailaddress (
    id integer NOT NULL,
    email character varying(254) NOT NULL,
    verified boolean NOT NULL,
    "primary" boolean NOT NULL,
    user_id bigint NOT NULL
);


ALTER TABLE public.account_emailaddress OWNER TO postgres;

--
-- Name: account_emailaddress_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.account_emailaddress ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.account_emailaddress_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: account_emailconfirmation; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.account_emailconfirmation (
    id integer NOT NULL,
    created timestamp with time zone NOT NULL,
    sent timestamp with time zone,
    key character varying(64) NOT NULL,
    email_address_id integer NOT NULL
);


ALTER TABLE public.account_emailconfirmation OWNER TO postgres;

--
-- Name: account_emailconfirmation_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.account_emailconfirmation ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.account_emailconfirmation_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: app_users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.app_users (
    id bigint NOT NULL,
    password character varying(128) NOT NULL,
    last_login timestamp with time zone,
    is_superuser boolean NOT NULL,
    first_name character varying(150) NOT NULL,
    last_name character varying(150) NOT NULL,
    email character varying(254),
    is_staff boolean NOT NULL,
    is_active boolean NOT NULL,
    date_joined timestamp with time zone NOT NULL,
    anonymous_id character varying(512),
    anonymous_id_verified timestamp with time zone,
    email_verified timestamp with time zone,
    phone_number character varying(255),
    phone_number_verified timestamp with time zone,
    checkout_phone_number character varying(255),
    photo_url character varying(255),
    address character varying(1024),
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL
);


ALTER TABLE public.app_users OWNER TO postgres;

--
-- Name: app_users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.app_users ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.app_users_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: artists; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.artists (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    name text NOT NULL,
    thumbnail character varying(100),
    thumbnail_url character varying(200)
);


ALTER TABLE public.artists OWNER TO postgres;

--
-- Name: artists_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.artists ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.artists_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_group; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.auth_group (
    id integer NOT NULL,
    name character varying(150) NOT NULL
);


ALTER TABLE public.auth_group OWNER TO postgres;

--
-- Name: auth_group_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.auth_group ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_group_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_group_permissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.auth_group_permissions (
    id bigint NOT NULL,
    group_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.auth_group_permissions OWNER TO postgres;

--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.auth_group_permissions ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_group_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_permission; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.auth_permission (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    content_type_id integer NOT NULL,
    codename character varying(100) NOT NULL
);


ALTER TABLE public.auth_permission OWNER TO postgres;

--
-- Name: auth_permission_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.auth_permission ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_permission_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: authentication_user; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.authentication_user (
    id bigint NOT NULL,
    last_login timestamp with time zone,
    is_superuser boolean NOT NULL,
    first_name character varying(150) NOT NULL,
    last_name character varying(150) NOT NULL,
    is_active boolean NOT NULL,
    date_joined timestamp with time zone NOT NULL,
    password character varying(128) NOT NULL,
    anonymous_id character varying(512),
    anonymous_id_verified timestamp with time zone,
    email character varying(254),
    email_verified timestamp with time zone,
    phone_number character varying(255),
    phone_number_verified timestamp with time zone,
    checkout_phone_number character varying(255),
    photo_url character varying(255),
    address character varying(1024),
    is_staff boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL
);


ALTER TABLE public.authentication_user OWNER TO postgres;

--
-- Name: authentication_user_groups; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.authentication_user_groups (
    id bigint NOT NULL,
    user_id bigint NOT NULL,
    group_id integer NOT NULL
);


ALTER TABLE public.authentication_user_groups OWNER TO postgres;

--
-- Name: authentication_user_groups_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.authentication_user_groups ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.authentication_user_groups_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: authentication_user_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.authentication_user ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.authentication_user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: authentication_user_user_permissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.authentication_user_user_permissions (
    id bigint NOT NULL,
    user_id bigint NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.authentication_user_user_permissions OWNER TO postgres;

--
-- Name: authentication_user_user_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.authentication_user_user_permissions ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.authentication_user_user_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: django_admin_log; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.django_admin_log (
    id integer NOT NULL,
    action_time timestamp with time zone NOT NULL,
    object_id text,
    object_repr character varying(200) NOT NULL,
    action_flag smallint NOT NULL,
    change_message text NOT NULL,
    content_type_id integer,
    user_id bigint NOT NULL,
    CONSTRAINT django_admin_log_action_flag_check CHECK ((action_flag >= 0))
);


ALTER TABLE public.django_admin_log OWNER TO postgres;

--
-- Name: django_admin_log_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.django_admin_log ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.django_admin_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: django_content_type; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.django_content_type (
    id integer NOT NULL,
    app_label character varying(100) NOT NULL,
    model character varying(100) NOT NULL
);


ALTER TABLE public.django_content_type OWNER TO postgres;

--
-- Name: django_content_type_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.django_content_type ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.django_content_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: django_migrations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.django_migrations (
    id bigint NOT NULL,
    app character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    applied timestamp with time zone NOT NULL
);


ALTER TABLE public.django_migrations OWNER TO postgres;

--
-- Name: django_migrations_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.django_migrations ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.django_migrations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: django_session; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.django_session (
    session_key character varying(40) NOT NULL,
    session_data text NOT NULL,
    expire_date timestamp with time zone NOT NULL
);


ALTER TABLE public.django_session OWNER TO postgres;

--
-- Name: guardian_groupobjectpermission; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.guardian_groupobjectpermission (
    id integer NOT NULL,
    object_pk character varying(255) NOT NULL,
    content_type_id integer NOT NULL,
    group_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.guardian_groupobjectpermission OWNER TO postgres;

--
-- Name: guardian_groupobjectpermission_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.guardian_groupobjectpermission ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.guardian_groupobjectpermission_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: guardian_userobjectpermission; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.guardian_userobjectpermission (
    id integer NOT NULL,
    object_pk character varying(255) NOT NULL,
    content_type_id integer NOT NULL,
    permission_id integer NOT NULL,
    user_id bigint NOT NULL
);


ALTER TABLE public.guardian_userobjectpermission OWNER TO postgres;

--
-- Name: guardian_userobjectpermission_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.guardian_userobjectpermission ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.guardian_userobjectpermission_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: listening_events; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.listening_events (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    session_id text,
    duration_seconds integer NOT NULL,
    start_time timestamp with time zone NOT NULL,
    end_time timestamp with time zone,
    ip_address inet,
    user_agent text,
    user_id bigint NOT NULL,
    station_id bigint NOT NULL,
    info jsonb
);


ALTER TABLE public.listening_events OWNER TO postgres;

--
-- Name: listening_events_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.listening_events ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.listening_events_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: posts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.posts (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    title text NOT NULL,
    link text NOT NULL,
    description text,
    published timestamp with time zone NOT NULL,
    station_id bigint NOT NULL
);


ALTER TABLE public.posts OWNER TO postgres;

--
-- Name: posts_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.posts ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.posts_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: reviews; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.reviews (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    stars integer NOT NULL,
    message text,
    verified boolean NOT NULL,
    user_id bigint NOT NULL,
    station_id bigint NOT NULL
);


ALTER TABLE public.reviews OWNER TO postgres;

--
-- Name: reviews_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.reviews ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.reviews_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: socialaccount_socialaccount; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.socialaccount_socialaccount (
    id integer NOT NULL,
    provider character varying(200) NOT NULL,
    uid character varying(191) NOT NULL,
    last_login timestamp with time zone NOT NULL,
    date_joined timestamp with time zone NOT NULL,
    extra_data jsonb NOT NULL,
    user_id bigint NOT NULL
);


ALTER TABLE public.socialaccount_socialaccount OWNER TO postgres;

--
-- Name: socialaccount_socialaccount_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.socialaccount_socialaccount ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.socialaccount_socialaccount_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: socialaccount_socialapp; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.socialaccount_socialapp (
    id integer NOT NULL,
    provider character varying(30) NOT NULL,
    name character varying(40) NOT NULL,
    client_id character varying(191) NOT NULL,
    secret character varying(191) NOT NULL,
    key character varying(191) NOT NULL,
    provider_id character varying(200) NOT NULL,
    settings jsonb NOT NULL
);


ALTER TABLE public.socialaccount_socialapp OWNER TO postgres;

--
-- Name: socialaccount_socialapp_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.socialaccount_socialapp ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.socialaccount_socialapp_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: socialaccount_socialtoken; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.socialaccount_socialtoken (
    id integer NOT NULL,
    token text NOT NULL,
    token_secret text NOT NULL,
    expires_at timestamp with time zone,
    account_id integer NOT NULL,
    app_id integer
);


ALTER TABLE public.socialaccount_socialtoken OWNER TO postgres;

--
-- Name: socialaccount_socialtoken_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.socialaccount_socialtoken ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.socialaccount_socialtoken_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: songs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.songs (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    name text NOT NULL,
    thumbnail character varying(100),
    thumbnail_url character varying(200),
    artist_id bigint
);


ALTER TABLE public.songs OWNER TO postgres;

--
-- Name: songs_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.songs ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.songs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: station_groups; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.station_groups (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    slug character varying(50) NOT NULL,
    name text NOT NULL,
    "order" double precision NOT NULL
);


ALTER TABLE public.station_groups OWNER TO postgres;

--
-- Name: station_groups_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.station_groups ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.station_groups_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: station_metadata_fetch_categories; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.station_metadata_fetch_categories (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    slug text NOT NULL
);


ALTER TABLE public.station_metadata_fetch_categories OWNER TO postgres;

--
-- Name: station_metadata_fetch_categories_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.station_metadata_fetch_categories ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.station_metadata_fetch_categories_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: station_streams; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.station_streams (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    stream_url text NOT NULL,
    "order" double precision,
    type text NOT NULL,
    station_id bigint NOT NULL
);


ALTER TABLE public.station_streams OWNER TO postgres;

--
-- Name: station_streams_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.station_streams ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.station_streams_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: station_to_station_group; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.station_to_station_group (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    "order" double precision,
    group_id bigint NOT NULL,
    station_id bigint NOT NULL
);


ALTER TABLE public.station_to_station_group OWNER TO postgres;

--
-- Name: station_to_station_group_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.station_to_station_group ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.station_to_station_group_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: stations_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.stations ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.stations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: stations_metadata_fetch; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.stations_metadata_fetch (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    "order" integer NOT NULL,
    url text NOT NULL,
    station_id bigint NOT NULL,
    station_metadata_fetch_category_id bigint NOT NULL
);


ALTER TABLE public.stations_metadata_fetch OWNER TO postgres;

--
-- Name: stations_metadata_fetch_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.stations_metadata_fetch ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.stations_metadata_fetch_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: stations_now_playing; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.stations_now_playing (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    raw_data jsonb NOT NULL,
    error jsonb,
    listeners integer,
    song_id bigint,
    station_id bigint NOT NULL
);


ALTER TABLE public.stations_now_playing OWNER TO postgres;

--
-- Name: stations_now_playing_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.stations_now_playing ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.stations_now_playing_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: stations_uptime; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.stations_uptime (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    is_up boolean NOT NULL,
    latency_ms integer NOT NULL,
    raw_data jsonb NOT NULL,
    station_id bigint NOT NULL
);


ALTER TABLE public.stations_uptime OWNER TO postgres;

--
-- Name: stations_uptime_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.stations_uptime ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.stations_uptime_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    password character varying(128) DEFAULT ''::character varying NOT NULL,
    last_login timestamp with time zone,
    is_superuser boolean DEFAULT false NOT NULL,
    first_name character varying(150) DEFAULT ''::character varying NOT NULL,
    last_name character varying(150) DEFAULT ''::character varying NOT NULL,
    email character varying(254),
    is_staff boolean DEFAULT true NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    date_joined timestamp with time zone DEFAULT now() NOT NULL,
    anonymous_id character varying(512),
    anonymous_id_verified timestamp with time zone,
    email_verified timestamp with time zone,
    phone_number character varying(255),
    phone_number_verified timestamp with time zone,
    checkout_phone_number character varying(255),
    photo_url character varying(255),
    address character varying(1024),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    modified_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: usersessions_usersession; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.usersessions_usersession (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    ip inet NOT NULL,
    last_seen_at timestamp with time zone NOT NULL,
    session_key text NOT NULL,
    user_agent character varying(200) NOT NULL,
    data jsonb NOT NULL,
    user_id bigint NOT NULL
);


ALTER TABLE public.usersessions_usersession OWNER TO postgres;

--
-- Name: usersessions_usersession_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.usersessions_usersession ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.usersessions_usersession_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Data for Name: hypertable; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.hypertable (id, schema_name, table_name, associated_schema_name, associated_table_prefix, num_dimensions, chunk_sizing_func_schema, chunk_sizing_func_name, chunk_target_size, compression_state, compressed_hypertable_id, status) FROM stdin;
\.


--
-- Data for Name: chunk; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.chunk (id, hypertable_id, schema_name, table_name, compressed_chunk_id, dropped, status, osm_chunk, creation_time) FROM stdin;
\.


--
-- Data for Name: chunk_column_stats; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.chunk_column_stats (id, hypertable_id, chunk_id, column_name, range_start, range_end, valid) FROM stdin;
\.


--
-- Data for Name: dimension; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.dimension (id, hypertable_id, column_name, column_type, aligned, num_slices, partitioning_func_schema, partitioning_func, interval_length, compress_interval_length, integer_now_func_schema, integer_now_func) FROM stdin;
\.


--
-- Data for Name: dimension_slice; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.dimension_slice (id, dimension_id, range_start, range_end) FROM stdin;
\.


--
-- Data for Name: chunk_constraint; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.chunk_constraint (chunk_id, dimension_slice_id, constraint_name, hypertable_constraint_name) FROM stdin;
\.


--
-- Data for Name: chunk_index; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.chunk_index (chunk_id, index_name, hypertable_id, hypertable_index_name) FROM stdin;
\.


--
-- Data for Name: compression_chunk_size; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.compression_chunk_size (chunk_id, compressed_chunk_id, uncompressed_heap_size, uncompressed_toast_size, uncompressed_index_size, compressed_heap_size, compressed_toast_size, compressed_index_size, numrows_pre_compression, numrows_post_compression, numrows_frozen_immediately) FROM stdin;
\.


--
-- Data for Name: compression_settings; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.compression_settings (relid, compress_relid, segmentby, orderby, orderby_desc, orderby_nullsfirst) FROM stdin;
\.


--
-- Data for Name: continuous_agg; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.continuous_agg (mat_hypertable_id, raw_hypertable_id, parent_mat_hypertable_id, user_view_schema, user_view_name, partial_view_schema, partial_view_name, direct_view_schema, direct_view_name, materialized_only, finalized) FROM stdin;
\.


--
-- Data for Name: continuous_agg_migrate_plan; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.continuous_agg_migrate_plan (mat_hypertable_id, start_ts, end_ts, user_view_definition) FROM stdin;
\.


--
-- Data for Name: continuous_agg_migrate_plan_step; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.continuous_agg_migrate_plan_step (mat_hypertable_id, step_id, status, start_ts, end_ts, type, config) FROM stdin;
\.


--
-- Data for Name: continuous_aggs_bucket_function; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.continuous_aggs_bucket_function (mat_hypertable_id, bucket_func, bucket_width, bucket_origin, bucket_offset, bucket_timezone, bucket_fixed_width) FROM stdin;
\.


--
-- Data for Name: continuous_aggs_hypertable_invalidation_log; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.continuous_aggs_hypertable_invalidation_log (hypertable_id, lowest_modified_value, greatest_modified_value) FROM stdin;
\.


--
-- Data for Name: continuous_aggs_invalidation_threshold; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.continuous_aggs_invalidation_threshold (hypertable_id, watermark) FROM stdin;
\.


--
-- Data for Name: continuous_aggs_materialization_invalidation_log; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.continuous_aggs_materialization_invalidation_log (materialization_id, lowest_modified_value, greatest_modified_value) FROM stdin;
\.


--
-- Data for Name: continuous_aggs_watermark; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.continuous_aggs_watermark (mat_hypertable_id, watermark) FROM stdin;
\.


--
-- Data for Name: metadata; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.metadata (key, value, include_in_telemetry) FROM stdin;
install_timestamp	2025-07-21 07:58:03.822975+00	t
timescaledb_version	2.20.0	f
\.


--
-- Data for Name: tablespace; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: postgres
--

COPY _timescaledb_catalog.tablespace (id, hypertable_id, tablespace_name) FROM stdin;
\.


--
-- Data for Name: bgw_job; Type: TABLE DATA; Schema: _timescaledb_config; Owner: postgres
--

COPY _timescaledb_config.bgw_job (id, application_name, schedule_interval, max_runtime, max_retries, retry_period, proc_schema, proc_name, owner, scheduled, fixed_schedule, initial_start, hypertable_id, config, check_schema, check_name, timezone) FROM stdin;
\.


--
-- Data for Name: hdb_action_log; Type: TABLE DATA; Schema: hdb_catalog; Owner: postgres
--

COPY hdb_catalog.hdb_action_log (id, action_name, input_payload, request_headers, session_variables, response_payload, errors, created_at, response_received_at, status) FROM stdin;
\.


--
-- Data for Name: hdb_cron_event_invocation_logs; Type: TABLE DATA; Schema: hdb_catalog; Owner: postgres
--

COPY hdb_catalog.hdb_cron_event_invocation_logs (id, event_id, status, request, response, created_at) FROM stdin;
\.


--
-- Data for Name: hdb_cron_events; Type: TABLE DATA; Schema: hdb_catalog; Owner: postgres
--

COPY hdb_catalog.hdb_cron_events (id, trigger_name, scheduled_time, status, tries, created_at, next_retry_at) FROM stdin;
\.


--
-- Data for Name: hdb_metadata; Type: TABLE DATA; Schema: hdb_catalog; Owner: postgres
--

COPY hdb_catalog.hdb_metadata (id, metadata, resource_version) FROM stdin;
1	{"sources":[{"configuration":{"connection_info":{"database_url":{"from_env":"HASURA_GRAPHQL_DATABASE_URL"},"isolation_level":"read-committed","pool_settings":{"connection_lifetime":600,"idle_timeout":180,"max_connections":20,"retries":1},"use_prepared_statements":true}},"kind":"postgres","name":"default","tables":[]}],"version":3}	1
\.


--
-- Data for Name: hdb_scheduled_event_invocation_logs; Type: TABLE DATA; Schema: hdb_catalog; Owner: postgres
--

COPY hdb_catalog.hdb_scheduled_event_invocation_logs (id, event_id, status, request, response, created_at) FROM stdin;
\.


--
-- Data for Name: hdb_scheduled_events; Type: TABLE DATA; Schema: hdb_catalog; Owner: postgres
--

COPY hdb_catalog.hdb_scheduled_events (id, webhook_conf, scheduled_time, retry_conf, payload, header_conf, status, tries, created_at, next_retry_at, comment) FROM stdin;
\.


--
-- Data for Name: hdb_schema_notifications; Type: TABLE DATA; Schema: hdb_catalog; Owner: postgres
--

COPY hdb_catalog.hdb_schema_notifications (id, notification, resource_version, instance_id, updated_at) FROM stdin;
\.


--
-- Data for Name: hdb_version; Type: TABLE DATA; Schema: hdb_catalog; Owner: postgres
--

COPY hdb_catalog.hdb_version (hasura_uuid, version, upgraded_on, cli_state, console_state, ee_client_id, ee_client_secret) FROM stdin;
4c902b31-5ebb-4c3d-b61d-205a90992b3a	48	2025-07-21 07:58:34.378946+00	{}	{}	\N	\N
\.


--
-- Data for Name: account_emailaddress; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.account_emailaddress (id, email, verified, "primary", user_id) FROM stdin;
\.


--
-- Data for Name: account_emailconfirmation; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.account_emailconfirmation (id, created, sent, key, email_address_id) FROM stdin;
\.


--
-- Data for Name: app_users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.app_users (id, password, last_login, is_superuser, first_name, last_name, email, is_staff, is_active, date_joined, anonymous_id, anonymous_id_verified, email_verified, phone_number, phone_number_verified, checkout_phone_number, photo_url, address, created_at, modified_at) FROM stdin;
\.


--
-- Data for Name: artists; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.artists (id, created_at, updated_at, name, thumbnail, thumbnail_url) FROM stdin;
\.


--
-- Data for Name: auth_group; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.auth_group (id, name) FROM stdin;
\.


--
-- Data for Name: auth_group_permissions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.auth_group_permissions (id, group_id, permission_id) FROM stdin;
\.


--
-- Data for Name: auth_permission; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.auth_permission (id, name, content_type_id, codename) FROM stdin;
1	Can add user	1	add_user
2	Can change user	1	change_user
3	Can delete user	1	delete_user
4	Can view user	1	view_user
5	Can view dashboard	1	can_view_dashboard
6	Can view custom page	1	can_view_custom_page
7	Is a normal user?	1	is_normal_user
8	Can add log entry	2	add_logentry
9	Can change log entry	2	change_logentry
10	Can delete log entry	2	delete_logentry
11	Can view log entry	2	view_logentry
12	Can add permission	3	add_permission
13	Can change permission	3	change_permission
14	Can delete permission	3	delete_permission
15	Can view permission	3	view_permission
16	Can add group	4	add_group
17	Can change group	4	change_group
18	Can delete group	4	delete_group
19	Can view group	4	view_group
20	Can add content type	5	add_contenttype
21	Can change content type	5	change_contenttype
22	Can delete content type	5	delete_contenttype
23	Can view content type	5	view_contenttype
24	Can add session	6	add_session
25	Can change session	6	change_session
26	Can delete session	6	delete_session
27	Can view session	6	view_session
28	Can add group object permission	7	add_groupobjectpermission
29	Can change group object permission	7	change_groupobjectpermission
30	Can delete group object permission	7	delete_groupobjectpermission
31	Can view group object permission	7	view_groupobjectpermission
32	Can add user object permission	8	add_userobjectpermission
33	Can change user object permission	8	change_userobjectpermission
34	Can delete user object permission	8	delete_userobjectpermission
35	Can view user object permission	8	view_userobjectpermission
36	Can add email address	9	add_emailaddress
37	Can change email address	9	change_emailaddress
38	Can delete email address	9	delete_emailaddress
39	Can view email address	9	view_emailaddress
40	Can add email confirmation	10	add_emailconfirmation
41	Can change email confirmation	10	change_emailconfirmation
42	Can delete email confirmation	10	delete_emailconfirmation
43	Can view email confirmation	10	view_emailconfirmation
44	Can add user session	11	add_usersession
45	Can change user session	11	change_usersession
46	Can delete user session	11	delete_usersession
47	Can view user session	11	view_usersession
48	Can add social account	12	add_socialaccount
49	Can change social account	12	change_socialaccount
50	Can delete social account	12	delete_socialaccount
51	Can view social account	12	view_socialaccount
52	Can add social application	13	add_socialapp
53	Can change social application	13	change_socialapp
54	Can delete social application	13	delete_socialapp
55	Can view social application	13	view_socialapp
56	Can add social application token	14	add_socialtoken
57	Can change social application token	14	change_socialtoken
58	Can delete social application token	14	delete_socialtoken
59	Can view social application token	14	view_socialtoken
60	Can add Station Group	15	add_stationgroups
61	Can change Station Group	15	change_stationgroups
62	Can delete Station Group	15	delete_stationgroups
63	Can view Station Group	15	view_stationgroups
64	Can add Station Metadata Fetch Category	16	add_stationmetadatafetchcategories
65	Can change Station Metadata Fetch Category	16	change_stationmetadatafetchcategories
66	Can delete Station Metadata Fetch Category	16	delete_stationmetadatafetchcategories
67	Can view Station Metadata Fetch Category	16	view_stationmetadatafetchcategories
68	Can add Station	17	add_stations
69	Can change Station	17	change_stations
70	Can delete Station	17	delete_stations
71	Can view Station	17	view_stations
72	Can add Artist	18	add_artists
73	Can change Artist	18	change_artists
74	Can delete Artist	18	delete_artists
75	Can view Artist	18	view_artists
76	Can add Song	19	add_songs
77	Can change Song	19	change_songs
78	Can delete Song	19	delete_songs
79	Can view Song	19	view_songs
80	Can add Post	20	add_posts
81	Can change Post	20	change_posts
82	Can delete Post	20	delete_posts
83	Can view Post	20	view_posts
84	Can add Listening Event	21	add_listeningevents
85	Can change Listening Event	21	change_listeningevents
86	Can delete Listening Event	21	delete_listeningevents
87	Can view Listening Event	21	view_listeningevents
88	Can add Station Metadata Fetch	22	add_stationsmetadatafetch
89	Can change Station Metadata Fetch	22	change_stationsmetadatafetch
90	Can delete Station Metadata Fetch	22	delete_stationsmetadatafetch
91	Can view Station Metadata Fetch	22	view_stationsmetadatafetch
92	Can add Station Now Playing	23	add_stationsnowplaying
93	Can change Station Now Playing	23	change_stationsnowplaying
94	Can delete Station Now Playing	23	delete_stationsnowplaying
95	Can view Station Now Playing	23	view_stationsnowplaying
96	Can add Station Uptime	24	add_stationsuptime
97	Can change Station Uptime	24	change_stationsuptime
98	Can delete Station Uptime	24	delete_stationsuptime
99	Can view Station Uptime	24	view_stationsuptime
100	Can add Station to Group Relationship	25	add_stationtostationgroup
101	Can change Station to Group Relationship	25	change_stationtostationgroup
102	Can delete Station to Group Relationship	25	delete_stationtostationgroup
103	Can view Station to Group Relationship	25	view_stationtostationgroup
104	Can add Review	26	add_reviews
105	Can change Review	26	change_reviews
106	Can delete Review	26	delete_reviews
107	Can view Review	26	view_reviews
108	Can add Station Stream	27	add_stationstreams
109	Can change Station Stream	27	change_stationstreams
110	Can delete Station Stream	27	delete_stationstreams
111	Can view Station Stream	27	view_stationstreams
112	Can add App User	28	add_appusers
113	Can change App User	28	change_appusers
114	Can delete App User	28	delete_appusers
115	Can view App User	28	view_appusers
\.


--
-- Data for Name: authentication_user; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.authentication_user (id, last_login, is_superuser, first_name, last_name, is_active, date_joined, password, anonymous_id, anonymous_id_verified, email, email_verified, phone_number, phone_number_verified, checkout_phone_number, photo_url, address, is_staff, created_at, modified_at) FROM stdin;
1	\N	f			t	2025-07-21 07:58:07.294645+00	!3hHsi6UWvj8tqD2ruDu93qcAVxuVDOFg7ElUmwF3	\N	\N	AnonymousUser	\N	\N	\N	\N	\N	\N	t	2025-07-21 07:58:07.294864+00	2025-07-21 07:58:07.294867+00
\.


--
-- Data for Name: authentication_user_groups; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.authentication_user_groups (id, user_id, group_id) FROM stdin;
\.


--
-- Data for Name: authentication_user_user_permissions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.authentication_user_user_permissions (id, user_id, permission_id) FROM stdin;
\.


--
-- Data for Name: django_admin_log; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.django_admin_log (id, action_time, object_id, object_repr, action_flag, change_message, content_type_id, user_id) FROM stdin;
\.


--
-- Data for Name: django_content_type; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.django_content_type (id, app_label, model) FROM stdin;
1	authentication	user
2	admin	logentry
3	auth	permission
4	auth	group
5	contenttypes	contenttype
6	sessions	session
7	guardian	groupobjectpermission
8	guardian	userobjectpermission
9	account	emailaddress
10	account	emailconfirmation
11	usersessions	usersession
12	socialaccount	socialaccount
13	socialaccount	socialapp
14	socialaccount	socialtoken
15	radio_crestin	stationgroups
16	radio_crestin	stationmetadatafetchcategories
17	radio_crestin	stations
18	radio_crestin	artists
19	radio_crestin	songs
20	radio_crestin	posts
21	radio_crestin	listeningevents
22	radio_crestin	stationsmetadatafetch
23	radio_crestin	stationsnowplaying
24	radio_crestin	stationsuptime
25	radio_crestin	stationtostationgroup
26	radio_crestin	reviews
27	radio_crestin	stationstreams
28	radio_crestin	appusers
\.


--
-- Data for Name: django_migrations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.django_migrations (id, app, name, applied) FROM stdin;
1	contenttypes	0001_initial	2025-07-21 07:58:05.87776+00
2	contenttypes	0002_remove_content_type_name	2025-07-21 07:58:05.881877+00
3	auth	0001_initial	2025-07-21 07:58:05.91266+00
4	auth	0002_alter_permission_name_max_length	2025-07-21 07:58:05.914988+00
5	auth	0003_alter_user_email_max_length	2025-07-21 07:58:05.917248+00
6	auth	0004_alter_user_username_opts	2025-07-21 07:58:05.919965+00
7	auth	0005_alter_user_last_login_null	2025-07-21 07:58:05.922303+00
8	auth	0006_require_contenttypes_0002	2025-07-21 07:58:05.92332+00
9	auth	0007_alter_validators_add_error_messages	2025-07-21 07:58:05.925606+00
10	auth	0008_alter_user_username_max_length	2025-07-21 07:58:05.927872+00
11	auth	0009_alter_user_last_name_max_length	2025-07-21 07:58:05.931711+00
12	auth	0010_alter_group_name_max_length	2025-07-21 07:58:05.936759+00
13	auth	0011_update_proxy_permissions	2025-07-21 07:58:05.943357+00
14	auth	0012_alter_user_first_name_max_length	2025-07-21 07:58:05.946728+00
15	authentication	0001_initial	2025-07-21 07:58:05.987247+00
16	account	0001_initial	2025-07-21 07:58:06.007379+00
17	account	0002_email_max_length	2025-07-21 07:58:06.011302+00
18	account	0003_alter_emailaddress_create_unique_verified_email	2025-07-21 07:58:06.020601+00
19	account	0004_alter_emailaddress_drop_unique_email	2025-07-21 07:58:06.029316+00
20	account	0005_emailaddress_idx_upper_email	2025-07-21 07:58:06.036775+00
21	account	0006_emailaddress_lower	2025-07-21 07:58:06.042857+00
22	account	0007_emailaddress_idx_email	2025-07-21 07:58:06.051843+00
23	account	0008_emailaddress_unique_primary_email_fixup	2025-07-21 07:58:06.059464+00
24	account	0009_emailaddress_unique_primary_email	2025-07-21 07:58:06.090686+00
25	admin	0001_initial	2025-07-21 07:58:06.170401+00
26	admin	0002_logentry_remove_auto_add	2025-07-21 07:58:06.177349+00
27	admin	0003_logentry_add_action_flag_choices	2025-07-21 07:58:06.184558+00
28	guardian	0001_initial	2025-07-21 07:58:06.24556+00
29	guardian	0002_generic_permissions_index	2025-07-21 07:58:06.266678+00
30	radio_crestin	0001_initial	2025-07-21 07:58:06.907252+00
31	radio_crestin	0002_listeningevents_info	2025-07-21 07:58:06.917625+00
32	radio_crestin	0003_create_users_view_and_computed_functions	2025-07-21 07:58:06.967166+00
33	radio_crestin	0004_fix_users_table_and_foreign_keys	2025-07-21 07:58:06.989161+00
34	radio_crestin	0005_fix_duplicate_foreign_keys	2025-07-21 07:58:06.991269+00
35	radio_crestin	0006_appusers_alter_listeningevents_user_and_more	2025-07-21 07:58:07.033126+00
36	radio_crestin	0007_alter_songs_unique_together_alter_songs_artist_and_more	2025-07-21 07:58:07.052527+00
37	sessions	0001_initial	2025-07-21 07:58:07.066705+00
38	socialaccount	0001_initial	2025-07-21 07:58:07.118461+00
39	socialaccount	0002_token_max_lengths	2025-07-21 07:58:07.131093+00
40	socialaccount	0003_extra_data_default_dict	2025-07-21 07:58:07.136862+00
41	socialaccount	0004_app_provider_id_settings	2025-07-21 07:58:07.148155+00
42	socialaccount	0005_socialtoken_nullable_app	2025-07-21 07:58:07.18773+00
43	socialaccount	0006_alter_socialaccount_extra_data	2025-07-21 07:58:07.206067+00
44	usersessions	0001_initial	2025-07-21 07:58:07.227958+00
45	usersessions	0002_alter_usersession_session_key	2025-07-21 07:58:07.235769+00
46	usersessions	0003_alter_usersession_session_key	2025-07-21 07:58:07.241836+00
\.


--
-- Data for Name: django_session; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.django_session (session_key, session_data, expire_date) FROM stdin;
\.


--
-- Data for Name: guardian_groupobjectpermission; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.guardian_groupobjectpermission (id, object_pk, content_type_id, group_id, permission_id) FROM stdin;
\.


--
-- Data for Name: guardian_userobjectpermission; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.guardian_userobjectpermission (id, object_pk, content_type_id, permission_id, user_id) FROM stdin;
\.


--
-- Data for Name: listening_events; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.listening_events (id, created_at, updated_at, session_id, duration_seconds, start_time, end_time, ip_address, user_agent, user_id, station_id, info) FROM stdin;
\.


--
-- Data for Name: posts; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.posts (id, created_at, updated_at, title, link, description, published, station_id) FROM stdin;
\.


--
-- Data for Name: reviews; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.reviews (id, created_at, updated_at, stars, message, verified, user_id, station_id) FROM stdin;
\.


--
-- Data for Name: socialaccount_socialaccount; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.socialaccount_socialaccount (id, provider, uid, last_login, date_joined, extra_data, user_id) FROM stdin;
\.


--
-- Data for Name: socialaccount_socialapp; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.socialaccount_socialapp (id, provider, name, client_id, secret, key, provider_id, settings) FROM stdin;
\.


--
-- Data for Name: socialaccount_socialtoken; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.socialaccount_socialtoken (id, token, token_secret, expires_at, account_id, app_id) FROM stdin;
\.


--
-- Data for Name: songs; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.songs (id, created_at, updated_at, name, thumbnail, thumbnail_url, artist_id) FROM stdin;
\.


--
-- Data for Name: station_groups; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.station_groups (id, created_at, updated_at, slug, name, "order") FROM stdin;
\.


--
-- Data for Name: station_metadata_fetch_categories; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.station_metadata_fetch_categories (id, created_at, updated_at, slug) FROM stdin;
\.


--
-- Data for Name: station_streams; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.station_streams (id, created_at, updated_at, stream_url, "order", type, station_id) FROM stdin;
\.


--
-- Data for Name: station_to_station_group; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.station_to_station_group (id, created_at, updated_at, "order", group_id, station_id) FROM stdin;
\.


--
-- Data for Name: stations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.stations (id, created_at, updated_at, disabled, "order", slug, title, website, email, generate_hls_stream, stream_url, thumbnail, thumbnail_url, description, description_action_title, description_link, rss_feed, feature_latest_post, facebook_page_id, latest_station_now_playing_id, latest_station_uptime_id) FROM stdin;
\.


--
-- Data for Name: stations_metadata_fetch; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.stations_metadata_fetch (id, created_at, updated_at, "order", url, station_id, station_metadata_fetch_category_id) FROM stdin;
\.


--
-- Data for Name: stations_now_playing; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.stations_now_playing (id, created_at, updated_at, "timestamp", raw_data, error, listeners, song_id, station_id) FROM stdin;
\.


--
-- Data for Name: stations_uptime; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.stations_uptime (id, created_at, updated_at, "timestamp", is_up, latency_ms, raw_data, station_id) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id, password, last_login, is_superuser, first_name, last_name, email, is_staff, is_active, date_joined, anonymous_id, anonymous_id_verified, email_verified, phone_number, phone_number_verified, checkout_phone_number, photo_url, address, created_at, modified_at) FROM stdin;
1	!3hHsi6UWvj8tqD2ruDu93qcAVxuVDOFg7ElUmwF3	\N	f			AnonymousUser	t	t	2025-07-21 07:58:07.294645+00	\N	\N	\N	\N	\N	\N	\N	\N	2025-07-21 07:58:07.294864+00	2025-07-21 07:58:07.294867+00
\.


--
-- Data for Name: usersessions_usersession; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.usersessions_usersession (id, created_at, ip, last_seen_at, session_key, user_agent, data, user_id) FROM stdin;
\.


--
-- Name: chunk_column_stats_id_seq; Type: SEQUENCE SET; Schema: _timescaledb_catalog; Owner: postgres
--

SELECT pg_catalog.setval('_timescaledb_catalog.chunk_column_stats_id_seq', 1, false);


--
-- Name: chunk_constraint_name; Type: SEQUENCE SET; Schema: _timescaledb_catalog; Owner: postgres
--

SELECT pg_catalog.setval('_timescaledb_catalog.chunk_constraint_name', 1, false);


--
-- Name: chunk_id_seq; Type: SEQUENCE SET; Schema: _timescaledb_catalog; Owner: postgres
--

SELECT pg_catalog.setval('_timescaledb_catalog.chunk_id_seq', 1, false);


--
-- Name: continuous_agg_migrate_plan_step_step_id_seq; Type: SEQUENCE SET; Schema: _timescaledb_catalog; Owner: postgres
--

SELECT pg_catalog.setval('_timescaledb_catalog.continuous_agg_migrate_plan_step_step_id_seq', 1, false);


--
-- Name: dimension_id_seq; Type: SEQUENCE SET; Schema: _timescaledb_catalog; Owner: postgres
--

SELECT pg_catalog.setval('_timescaledb_catalog.dimension_id_seq', 1, false);


--
-- Name: dimension_slice_id_seq; Type: SEQUENCE SET; Schema: _timescaledb_catalog; Owner: postgres
--

SELECT pg_catalog.setval('_timescaledb_catalog.dimension_slice_id_seq', 1, false);


--
-- Name: hypertable_id_seq; Type: SEQUENCE SET; Schema: _timescaledb_catalog; Owner: postgres
--

SELECT pg_catalog.setval('_timescaledb_catalog.hypertable_id_seq', 1, false);


--
-- Name: bgw_job_id_seq; Type: SEQUENCE SET; Schema: _timescaledb_config; Owner: postgres
--

SELECT pg_catalog.setval('_timescaledb_config.bgw_job_id_seq', 1000, false);


--
-- Name: account_emailaddress_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.account_emailaddress_id_seq', 1, false);


--
-- Name: account_emailconfirmation_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.account_emailconfirmation_id_seq', 1, false);


--
-- Name: app_users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.app_users_id_seq', 1, false);


--
-- Name: artists_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.artists_id_seq', 1, false);


--
-- Name: auth_group_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.auth_group_id_seq', 1, false);


--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.auth_group_permissions_id_seq', 1, false);


--
-- Name: auth_permission_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.auth_permission_id_seq', 115, true);


--
-- Name: authentication_user_groups_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.authentication_user_groups_id_seq', 1, false);


--
-- Name: authentication_user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.authentication_user_id_seq', 1, true);


--
-- Name: authentication_user_user_permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.authentication_user_user_permissions_id_seq', 1, false);


--
-- Name: django_admin_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.django_admin_log_id_seq', 1, false);


--
-- Name: django_content_type_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.django_content_type_id_seq', 28, true);


--
-- Name: django_migrations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.django_migrations_id_seq', 46, true);


--
-- Name: guardian_groupobjectpermission_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.guardian_groupobjectpermission_id_seq', 1, false);


--
-- Name: guardian_userobjectpermission_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.guardian_userobjectpermission_id_seq', 1, false);


--
-- Name: listening_events_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.listening_events_id_seq', 1, false);


--
-- Name: posts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.posts_id_seq', 1, false);


--
-- Name: reviews_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.reviews_id_seq', 1, false);


--
-- Name: socialaccount_socialaccount_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.socialaccount_socialaccount_id_seq', 1, false);


--
-- Name: socialaccount_socialapp_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.socialaccount_socialapp_id_seq', 1, false);


--
-- Name: socialaccount_socialtoken_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.socialaccount_socialtoken_id_seq', 1, false);


--
-- Name: songs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.songs_id_seq', 1, false);


--
-- Name: station_groups_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.station_groups_id_seq', 1, false);


--
-- Name: station_metadata_fetch_categories_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.station_metadata_fetch_categories_id_seq', 1, false);


--
-- Name: station_streams_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.station_streams_id_seq', 1, false);


--
-- Name: station_to_station_group_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.station_to_station_group_id_seq', 1, false);


--
-- Name: stations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.stations_id_seq', 1, false);


--
-- Name: stations_metadata_fetch_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.stations_metadata_fetch_id_seq', 1, false);


--
-- Name: stations_now_playing_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.stations_now_playing_id_seq', 1, false);


--
-- Name: stations_uptime_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.stations_uptime_id_seq', 1, false);


--
-- Name: usersessions_usersession_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.usersessions_usersession_id_seq', 1, false);


--
-- Name: hdb_action_log hdb_action_log_pkey; Type: CONSTRAINT; Schema: hdb_catalog; Owner: postgres
--

ALTER TABLE ONLY hdb_catalog.hdb_action_log
    ADD CONSTRAINT hdb_action_log_pkey PRIMARY KEY (id);


--
-- Name: hdb_cron_event_invocation_logs hdb_cron_event_invocation_logs_pkey; Type: CONSTRAINT; Schema: hdb_catalog; Owner: postgres
--

ALTER TABLE ONLY hdb_catalog.hdb_cron_event_invocation_logs
    ADD CONSTRAINT hdb_cron_event_invocation_logs_pkey PRIMARY KEY (id);


--
-- Name: hdb_cron_events hdb_cron_events_pkey; Type: CONSTRAINT; Schema: hdb_catalog; Owner: postgres
--

ALTER TABLE ONLY hdb_catalog.hdb_cron_events
    ADD CONSTRAINT hdb_cron_events_pkey PRIMARY KEY (id);


--
-- Name: hdb_metadata hdb_metadata_pkey; Type: CONSTRAINT; Schema: hdb_catalog; Owner: postgres
--

ALTER TABLE ONLY hdb_catalog.hdb_metadata
    ADD CONSTRAINT hdb_metadata_pkey PRIMARY KEY (id);


--
-- Name: hdb_metadata hdb_metadata_resource_version_key; Type: CONSTRAINT; Schema: hdb_catalog; Owner: postgres
--

ALTER TABLE ONLY hdb_catalog.hdb_metadata
    ADD CONSTRAINT hdb_metadata_resource_version_key UNIQUE (resource_version);


--
-- Name: hdb_scheduled_event_invocation_logs hdb_scheduled_event_invocation_logs_pkey; Type: CONSTRAINT; Schema: hdb_catalog; Owner: postgres
--

ALTER TABLE ONLY hdb_catalog.hdb_scheduled_event_invocation_logs
    ADD CONSTRAINT hdb_scheduled_event_invocation_logs_pkey PRIMARY KEY (id);


--
-- Name: hdb_scheduled_events hdb_scheduled_events_pkey; Type: CONSTRAINT; Schema: hdb_catalog; Owner: postgres
--

ALTER TABLE ONLY hdb_catalog.hdb_scheduled_events
    ADD CONSTRAINT hdb_scheduled_events_pkey PRIMARY KEY (id);


--
-- Name: hdb_schema_notifications hdb_schema_notifications_pkey; Type: CONSTRAINT; Schema: hdb_catalog; Owner: postgres
--

ALTER TABLE ONLY hdb_catalog.hdb_schema_notifications
    ADD CONSTRAINT hdb_schema_notifications_pkey PRIMARY KEY (id);


--
-- Name: hdb_version hdb_version_pkey; Type: CONSTRAINT; Schema: hdb_catalog; Owner: postgres
--

ALTER TABLE ONLY hdb_catalog.hdb_version
    ADD CONSTRAINT hdb_version_pkey PRIMARY KEY (hasura_uuid);


--
-- Name: account_emailaddress account_emailaddress_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.account_emailaddress
    ADD CONSTRAINT account_emailaddress_pkey PRIMARY KEY (id);


--
-- Name: account_emailaddress account_emailaddress_user_id_email_987c8728_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.account_emailaddress
    ADD CONSTRAINT account_emailaddress_user_id_email_987c8728_uniq UNIQUE (user_id, email);


--
-- Name: account_emailconfirmation account_emailconfirmation_key_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.account_emailconfirmation
    ADD CONSTRAINT account_emailconfirmation_key_key UNIQUE (key);


--
-- Name: account_emailconfirmation account_emailconfirmation_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.account_emailconfirmation
    ADD CONSTRAINT account_emailconfirmation_pkey PRIMARY KEY (id);


--
-- Name: app_users app_users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.app_users
    ADD CONSTRAINT app_users_pkey PRIMARY KEY (id);


--
-- Name: artists artists_name_007bb7fc_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.artists
    ADD CONSTRAINT artists_name_007bb7fc_uniq UNIQUE (name);


--
-- Name: artists artists_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.artists
    ADD CONSTRAINT artists_pkey PRIMARY KEY (id);


--
-- Name: auth_group auth_group_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_name_key UNIQUE (name);


--
-- Name: auth_group_permissions auth_group_permissions_group_id_permission_id_0cd325b0_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_permission_id_0cd325b0_uniq UNIQUE (group_id, permission_id);


--
-- Name: auth_group_permissions auth_group_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_pkey PRIMARY KEY (id);


--
-- Name: auth_group auth_group_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_pkey PRIMARY KEY (id);


--
-- Name: auth_permission auth_permission_content_type_id_codename_01ab375a_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_codename_01ab375a_uniq UNIQUE (content_type_id, codename);


--
-- Name: auth_permission auth_permission_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_pkey PRIMARY KEY (id);


--
-- Name: authentication_user authentication_user_anonymous_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.authentication_user
    ADD CONSTRAINT authentication_user_anonymous_id_key UNIQUE (anonymous_id);


--
-- Name: authentication_user authentication_user_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.authentication_user
    ADD CONSTRAINT authentication_user_email_key UNIQUE (email);


--
-- Name: authentication_user_groups authentication_user_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.authentication_user_groups
    ADD CONSTRAINT authentication_user_groups_pkey PRIMARY KEY (id);


--
-- Name: authentication_user_groups authentication_user_groups_user_id_group_id_8af031ac_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.authentication_user_groups
    ADD CONSTRAINT authentication_user_groups_user_id_group_id_8af031ac_uniq UNIQUE (user_id, group_id);


--
-- Name: authentication_user authentication_user_phone_number_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.authentication_user
    ADD CONSTRAINT authentication_user_phone_number_key UNIQUE (phone_number);


--
-- Name: authentication_user authentication_user_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.authentication_user
    ADD CONSTRAINT authentication_user_pkey PRIMARY KEY (id);


--
-- Name: authentication_user_user_permissions authentication_user_user_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.authentication_user_user_permissions
    ADD CONSTRAINT authentication_user_user_permissions_pkey PRIMARY KEY (id);


--
-- Name: authentication_user_user_permissions authentication_user_user_user_id_permission_id_ec51b09f_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.authentication_user_user_permissions
    ADD CONSTRAINT authentication_user_user_user_id_permission_id_ec51b09f_uniq UNIQUE (user_id, permission_id);


--
-- Name: django_admin_log django_admin_log_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_pkey PRIMARY KEY (id);


--
-- Name: django_content_type django_content_type_app_label_model_76bd3d3b_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_app_label_model_76bd3d3b_uniq UNIQUE (app_label, model);


--
-- Name: django_content_type django_content_type_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_pkey PRIMARY KEY (id);


--
-- Name: django_migrations django_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_migrations
    ADD CONSTRAINT django_migrations_pkey PRIMARY KEY (id);


--
-- Name: django_session django_session_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_session
    ADD CONSTRAINT django_session_pkey PRIMARY KEY (session_key);


--
-- Name: guardian_groupobjectpermission guardian_groupobjectperm_group_id_permission_id_o_3f189f7c_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.guardian_groupobjectpermission
    ADD CONSTRAINT guardian_groupobjectperm_group_id_permission_id_o_3f189f7c_uniq UNIQUE (group_id, permission_id, object_pk);


--
-- Name: guardian_groupobjectpermission guardian_groupobjectpermission_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.guardian_groupobjectpermission
    ADD CONSTRAINT guardian_groupobjectpermission_pkey PRIMARY KEY (id);


--
-- Name: guardian_userobjectpermission guardian_userobjectpermi_user_id_permission_id_ob_b0b3d2fc_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.guardian_userobjectpermission
    ADD CONSTRAINT guardian_userobjectpermi_user_id_permission_id_ob_b0b3d2fc_uniq UNIQUE (user_id, permission_id, object_pk);


--
-- Name: guardian_userobjectpermission guardian_userobjectpermission_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.guardian_userobjectpermission
    ADD CONSTRAINT guardian_userobjectpermission_pkey PRIMARY KEY (id);


--
-- Name: listening_events listening_events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.listening_events
    ADD CONSTRAINT listening_events_pkey PRIMARY KEY (id);


--
-- Name: posts posts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.posts
    ADD CONSTRAINT posts_pkey PRIMARY KEY (id);


--
-- Name: reviews reviews_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_pkey PRIMARY KEY (id);


--
-- Name: reviews reviews_station_id_user_id_224fbc42_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_station_id_user_id_224fbc42_uniq UNIQUE (station_id, user_id);


--
-- Name: socialaccount_socialaccount socialaccount_socialaccount_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.socialaccount_socialaccount
    ADD CONSTRAINT socialaccount_socialaccount_pkey PRIMARY KEY (id);


--
-- Name: socialaccount_socialaccount socialaccount_socialaccount_provider_uid_fc810c6e_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.socialaccount_socialaccount
    ADD CONSTRAINT socialaccount_socialaccount_provider_uid_fc810c6e_uniq UNIQUE (provider, uid);


--
-- Name: socialaccount_socialapp socialaccount_socialapp_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.socialaccount_socialapp
    ADD CONSTRAINT socialaccount_socialapp_pkey PRIMARY KEY (id);


--
-- Name: socialaccount_socialtoken socialaccount_socialtoken_app_id_account_id_fca4e0ac_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.socialaccount_socialtoken
    ADD CONSTRAINT socialaccount_socialtoken_app_id_account_id_fca4e0ac_uniq UNIQUE (app_id, account_id);


--
-- Name: socialaccount_socialtoken socialaccount_socialtoken_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.socialaccount_socialtoken
    ADD CONSTRAINT socialaccount_socialtoken_pkey PRIMARY KEY (id);


--
-- Name: songs songs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.songs
    ADD CONSTRAINT songs_pkey PRIMARY KEY (id);


--
-- Name: station_groups station_groups_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.station_groups
    ADD CONSTRAINT station_groups_name_key UNIQUE (name);


--
-- Name: station_groups station_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.station_groups
    ADD CONSTRAINT station_groups_pkey PRIMARY KEY (id);


--
-- Name: station_metadata_fetch_categories station_metadata_fetch_categories_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.station_metadata_fetch_categories
    ADD CONSTRAINT station_metadata_fetch_categories_pkey PRIMARY KEY (id);


--
-- Name: station_metadata_fetch_categories station_metadata_fetch_categories_slug_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.station_metadata_fetch_categories
    ADD CONSTRAINT station_metadata_fetch_categories_slug_key UNIQUE (slug);


--
-- Name: station_streams station_streams_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.station_streams
    ADD CONSTRAINT station_streams_pkey PRIMARY KEY (id);


--
-- Name: station_streams station_streams_station_id_stream_url_1054d81d_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.station_streams
    ADD CONSTRAINT station_streams_station_id_stream_url_1054d81d_uniq UNIQUE (station_id, stream_url);


--
-- Name: station_to_station_group station_to_station_group_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.station_to_station_group
    ADD CONSTRAINT station_to_station_group_pkey PRIMARY KEY (id);


--
-- Name: station_to_station_group station_to_station_group_station_id_group_id_706290d6_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.station_to_station_group
    ADD CONSTRAINT station_to_station_group_station_id_group_id_706290d6_uniq UNIQUE (station_id, group_id);


--
-- Name: stations_metadata_fetch stations_metadata_fetch_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stations_metadata_fetch
    ADD CONSTRAINT stations_metadata_fetch_pkey PRIMARY KEY (id);


--
-- Name: stations_now_playing stations_now_playing_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stations_now_playing
    ADD CONSTRAINT stations_now_playing_pkey PRIMARY KEY (id);


--
-- Name: stations_now_playing stations_now_playing_station_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stations_now_playing
    ADD CONSTRAINT stations_now_playing_station_id_key UNIQUE (station_id);


--
-- Name: stations stations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stations
    ADD CONSTRAINT stations_pkey PRIMARY KEY (id);


--
-- Name: stations_uptime stations_uptime_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stations_uptime
    ADD CONSTRAINT stations_uptime_pkey PRIMARY KEY (id);


--
-- Name: stations_uptime stations_uptime_station_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stations_uptime
    ADD CONSTRAINT stations_uptime_station_id_key UNIQUE (station_id);


--
-- Name: users unique_users_anonymous_id; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT unique_users_anonymous_id UNIQUE (anonymous_id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: users unique_users_email; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT unique_users_email UNIQUE (email) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: users unique_users_phone_number; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT unique_users_phone_number UNIQUE (phone_number) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: usersessions_usersession usersessions_usersession_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usersessions_usersession
    ADD CONSTRAINT usersessions_usersession_pkey PRIMARY KEY (id);


--
-- Name: usersessions_usersession usersessions_usersession_session_key_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usersessions_usersession
    ADD CONSTRAINT usersessions_usersession_session_key_key UNIQUE (session_key);


--
-- Name: hdb_cron_event_invocation_event_id; Type: INDEX; Schema: hdb_catalog; Owner: postgres
--

CREATE INDEX hdb_cron_event_invocation_event_id ON hdb_catalog.hdb_cron_event_invocation_logs USING btree (event_id);


--
-- Name: hdb_cron_event_status; Type: INDEX; Schema: hdb_catalog; Owner: postgres
--

CREATE INDEX hdb_cron_event_status ON hdb_catalog.hdb_cron_events USING btree (status);


--
-- Name: hdb_cron_events_unique_scheduled; Type: INDEX; Schema: hdb_catalog; Owner: postgres
--

CREATE UNIQUE INDEX hdb_cron_events_unique_scheduled ON hdb_catalog.hdb_cron_events USING btree (trigger_name, scheduled_time) WHERE (status = 'scheduled'::text);


--
-- Name: hdb_scheduled_event_status; Type: INDEX; Schema: hdb_catalog; Owner: postgres
--

CREATE INDEX hdb_scheduled_event_status ON hdb_catalog.hdb_scheduled_events USING btree (status);


--
-- Name: hdb_version_one_row; Type: INDEX; Schema: hdb_catalog; Owner: postgres
--

CREATE UNIQUE INDEX hdb_version_one_row ON hdb_catalog.hdb_version USING btree (((version IS NOT NULL)));


--
-- Name: account_emailaddress_email_03be32b2; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX account_emailaddress_email_03be32b2 ON public.account_emailaddress USING btree (email);


--
-- Name: account_emailaddress_email_03be32b2_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX account_emailaddress_email_03be32b2_like ON public.account_emailaddress USING btree (email varchar_pattern_ops);


--
-- Name: account_emailaddress_user_id_2c513194; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX account_emailaddress_user_id_2c513194 ON public.account_emailaddress USING btree (user_id);


--
-- Name: account_emailconfirmation_email_address_id_5b7f8c58; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX account_emailconfirmation_email_address_id_5b7f8c58 ON public.account_emailconfirmation USING btree (email_address_id);


--
-- Name: account_emailconfirmation_key_f43612bd_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX account_emailconfirmation_key_f43612bd_like ON public.account_emailconfirmation USING btree (key varchar_pattern_ops);


--
-- Name: auth_group_name_a6ea08ec_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX auth_group_name_a6ea08ec_like ON public.auth_group USING btree (name varchar_pattern_ops);


--
-- Name: auth_group_permissions_group_id_b120cbf9; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX auth_group_permissions_group_id_b120cbf9 ON public.auth_group_permissions USING btree (group_id);


--
-- Name: auth_group_permissions_permission_id_84c5c92e; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX auth_group_permissions_permission_id_84c5c92e ON public.auth_group_permissions USING btree (permission_id);


--
-- Name: auth_permission_content_type_id_2f476e4b; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX auth_permission_content_type_id_2f476e4b ON public.auth_permission USING btree (content_type_id);


--
-- Name: authentication_user_anonymous_id_d5014230_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX authentication_user_anonymous_id_d5014230_like ON public.authentication_user USING btree (anonymous_id varchar_pattern_ops);


--
-- Name: authentication_user_email_2220eff5_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX authentication_user_email_2220eff5_like ON public.authentication_user USING btree (email varchar_pattern_ops);


--
-- Name: authentication_user_groups_group_id_6b5c44b7; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX authentication_user_groups_group_id_6b5c44b7 ON public.authentication_user_groups USING btree (group_id);


--
-- Name: authentication_user_groups_user_id_30868577; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX authentication_user_groups_user_id_30868577 ON public.authentication_user_groups USING btree (user_id);


--
-- Name: authentication_user_phone_number_f8159965_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX authentication_user_phone_number_f8159965_like ON public.authentication_user USING btree (phone_number varchar_pattern_ops);


--
-- Name: authentication_user_user_permissions_permission_id_ea6be19a; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX authentication_user_user_permissions_permission_id_ea6be19a ON public.authentication_user_user_permissions USING btree (permission_id);


--
-- Name: authentication_user_user_permissions_user_id_736ebf7e; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX authentication_user_user_permissions_user_id_736ebf7e ON public.authentication_user_user_permissions USING btree (user_id);


--
-- Name: django_admin_log_content_type_id_c4bce8eb; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX django_admin_log_content_type_id_c4bce8eb ON public.django_admin_log USING btree (content_type_id);


--
-- Name: django_admin_log_user_id_c564eba6; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX django_admin_log_user_id_c564eba6 ON public.django_admin_log USING btree (user_id);


--
-- Name: django_session_expire_date_a5c62663; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX django_session_expire_date_a5c62663 ON public.django_session USING btree (expire_date);


--
-- Name: django_session_session_key_c0390e0f_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX django_session_session_key_c0390e0f_like ON public.django_session USING btree (session_key varchar_pattern_ops);


--
-- Name: guardian_gr_content_ae6aec_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX guardian_gr_content_ae6aec_idx ON public.guardian_groupobjectpermission USING btree (content_type_id, object_pk);


--
-- Name: guardian_groupobjectpermission_content_type_id_7ade36b8; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX guardian_groupobjectpermission_content_type_id_7ade36b8 ON public.guardian_groupobjectpermission USING btree (content_type_id);


--
-- Name: guardian_groupobjectpermission_group_id_4bbbfb62; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX guardian_groupobjectpermission_group_id_4bbbfb62 ON public.guardian_groupobjectpermission USING btree (group_id);


--
-- Name: guardian_groupobjectpermission_permission_id_36572738; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX guardian_groupobjectpermission_permission_id_36572738 ON public.guardian_groupobjectpermission USING btree (permission_id);


--
-- Name: guardian_us_content_179ed2_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX guardian_us_content_179ed2_idx ON public.guardian_userobjectpermission USING btree (content_type_id, object_pk);


--
-- Name: guardian_userobjectpermission_content_type_id_2e892405; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX guardian_userobjectpermission_content_type_id_2e892405 ON public.guardian_userobjectpermission USING btree (content_type_id);


--
-- Name: guardian_userobjectpermission_permission_id_71807bfc; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX guardian_userobjectpermission_permission_id_71807bfc ON public.guardian_userobjectpermission USING btree (permission_id);


--
-- Name: guardian_userobjectpermission_user_id_d5c1e964; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX guardian_userobjectpermission_user_id_d5c1e964 ON public.guardian_userobjectpermission USING btree (user_id);


--
-- Name: idx_listening_events_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_listening_events_created_at ON public.listening_events USING btree (created_at);


--
-- Name: idx_listening_events_station_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_listening_events_station_id ON public.listening_events USING btree (station_id);


--
-- Name: idx_listening_events_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_listening_events_user_id ON public.listening_events USING btree (user_id);


--
-- Name: listening_events_station_id_c913e7ee; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX listening_events_station_id_c913e7ee ON public.listening_events USING btree (station_id);


--
-- Name: listening_events_user_id_3170c89a; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX listening_events_user_id_3170c89a ON public.listening_events USING btree (user_id);


--
-- Name: posts_station_id_2ce2b217; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX posts_station_id_2ce2b217 ON public.posts USING btree (station_id);


--
-- Name: reviews_station_id_8b7ea576; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX reviews_station_id_8b7ea576 ON public.reviews USING btree (station_id);


--
-- Name: reviews_user_id_c23b0903; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX reviews_user_id_c23b0903 ON public.reviews USING btree (user_id);


--
-- Name: socialaccount_socialaccount_user_id_8146e70c; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX socialaccount_socialaccount_user_id_8146e70c ON public.socialaccount_socialaccount USING btree (user_id);


--
-- Name: socialaccount_socialtoken_account_id_951f210e; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX socialaccount_socialtoken_account_id_951f210e ON public.socialaccount_socialtoken USING btree (account_id);


--
-- Name: socialaccount_socialtoken_app_id_636a42d7; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX socialaccount_socialtoken_app_id_636a42d7 ON public.socialaccount_socialtoken USING btree (app_id);


--
-- Name: songs_artist_id_cd88e06f; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX songs_artist_id_cd88e06f ON public.songs USING btree (artist_id);


--
-- Name: station_groups_name_938e58ee_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX station_groups_name_938e58ee_like ON public.station_groups USING btree (name text_pattern_ops);


--
-- Name: station_groups_slug_1a8ef2cd; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX station_groups_slug_1a8ef2cd ON public.station_groups USING btree (slug);


--
-- Name: station_groups_slug_1a8ef2cd_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX station_groups_slug_1a8ef2cd_like ON public.station_groups USING btree (slug varchar_pattern_ops);


--
-- Name: station_metadata_fetch_categories_slug_3fcba937_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX station_metadata_fetch_categories_slug_3fcba937_like ON public.station_metadata_fetch_categories USING btree (slug text_pattern_ops);


--
-- Name: station_streams_station_id_ed34a3f7; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX station_streams_station_id_ed34a3f7 ON public.station_streams USING btree (station_id);


--
-- Name: station_to_station_group_group_id_8774970d; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX station_to_station_group_group_id_8774970d ON public.station_to_station_group USING btree (group_id);


--
-- Name: station_to_station_group_station_id_ec59ee7a; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX station_to_station_group_station_id_ec59ee7a ON public.station_to_station_group USING btree (station_id);


--
-- Name: stations_latest_station_now_playing_id_0be7a339; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX stations_latest_station_now_playing_id_0be7a339 ON public.stations USING btree (latest_station_now_playing_id);


--
-- Name: stations_latest_station_uptime_id_9ef73963; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX stations_latest_station_uptime_id_9ef73963 ON public.stations USING btree (latest_station_uptime_id);


--
-- Name: stations_metadata_fetch_station_id_3c1793db; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX stations_metadata_fetch_station_id_3c1793db ON public.stations_metadata_fetch USING btree (station_id);


--
-- Name: stations_metadata_fetch_station_metadata_fetch_cat_654b6d10; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX stations_metadata_fetch_station_metadata_fetch_cat_654b6d10 ON public.stations_metadata_fetch USING btree (station_metadata_fetch_category_id);


--
-- Name: stations_now_playing_song_id_29de6a79; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX stations_now_playing_song_id_29de6a79 ON public.stations_now_playing USING btree (song_id);


--
-- Name: stations_slug_ae0ba215; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX stations_slug_ae0ba215 ON public.stations USING btree (slug);


--
-- Name: stations_slug_ae0ba215_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX stations_slug_ae0ba215_like ON public.stations USING btree (slug varchar_pattern_ops);


--
-- Name: unique_anonymous_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX unique_anonymous_id ON public.authentication_user USING btree (anonymous_id) WHERE (NOT (anonymous_id IS NULL));


--
-- Name: unique_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX unique_email ON public.authentication_user USING btree (email) WHERE (NOT (email IS NULL));


--
-- Name: unique_phone_number; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX unique_phone_number ON public.authentication_user USING btree (phone_number) WHERE (NOT (phone_number IS NULL));


--
-- Name: unique_primary_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX unique_primary_email ON public.account_emailaddress USING btree (user_id, "primary") WHERE "primary";


--
-- Name: unique_song_artist; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX unique_song_artist ON public.songs USING btree (name, artist_id) WHERE (artist_id IS NOT NULL);


--
-- Name: unique_song_no_artist; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX unique_song_no_artist ON public.songs USING btree (name) WHERE (artist_id IS NULL);


--
-- Name: unique_verified_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX unique_verified_email ON public.account_emailaddress USING btree (email) WHERE verified;


--
-- Name: usersessions_usersession_user_id_af5e0a6d; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX usersessions_usersession_user_id_af5e0a6d ON public.usersessions_usersession USING btree (user_id);


--
-- Name: authentication_user sync_users_delete; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER sync_users_delete AFTER DELETE ON public.authentication_user FOR EACH ROW EXECUTE FUNCTION public.sync_users_table();


--
-- Name: authentication_user sync_users_insert; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER sync_users_insert AFTER INSERT ON public.authentication_user FOR EACH ROW EXECUTE FUNCTION public.sync_users_table();


--
-- Name: authentication_user sync_users_update; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER sync_users_update AFTER UPDATE ON public.authentication_user FOR EACH ROW EXECUTE FUNCTION public.sync_users_table();


--
-- Name: hdb_cron_event_invocation_logs hdb_cron_event_invocation_logs_event_id_fkey; Type: FK CONSTRAINT; Schema: hdb_catalog; Owner: postgres
--

ALTER TABLE ONLY hdb_catalog.hdb_cron_event_invocation_logs
    ADD CONSTRAINT hdb_cron_event_invocation_logs_event_id_fkey FOREIGN KEY (event_id) REFERENCES hdb_catalog.hdb_cron_events(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: hdb_scheduled_event_invocation_logs hdb_scheduled_event_invocation_logs_event_id_fkey; Type: FK CONSTRAINT; Schema: hdb_catalog; Owner: postgres
--

ALTER TABLE ONLY hdb_catalog.hdb_scheduled_event_invocation_logs
    ADD CONSTRAINT hdb_scheduled_event_invocation_logs_event_id_fkey FOREIGN KEY (event_id) REFERENCES hdb_catalog.hdb_scheduled_events(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: account_emailaddress account_emailaddress_user_id_2c513194_fk_authentication_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.account_emailaddress
    ADD CONSTRAINT account_emailaddress_user_id_2c513194_fk_authentication_user_id FOREIGN KEY (user_id) REFERENCES public.authentication_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: account_emailconfirmation account_emailconfirm_email_address_id_5b7f8c58_fk_account_e; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.account_emailconfirmation
    ADD CONSTRAINT account_emailconfirm_email_address_id_5b7f8c58_fk_account_e FOREIGN KEY (email_address_id) REFERENCES public.account_emailaddress(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_group_permissions auth_group_permissio_permission_id_84c5c92e_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissio_permission_id_84c5c92e_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_group_permissions auth_group_permissions_group_id_b120cbf9_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_b120cbf9_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_permission auth_permission_content_type_id_2f476e4b_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_2f476e4b_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: authentication_user_user_permissions authentication_user__permission_id_ea6be19a_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.authentication_user_user_permissions
    ADD CONSTRAINT authentication_user__permission_id_ea6be19a_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: authentication_user_groups authentication_user__user_id_30868577_fk_authentic; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.authentication_user_groups
    ADD CONSTRAINT authentication_user__user_id_30868577_fk_authentic FOREIGN KEY (user_id) REFERENCES public.authentication_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: authentication_user_user_permissions authentication_user__user_id_736ebf7e_fk_authentic; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.authentication_user_user_permissions
    ADD CONSTRAINT authentication_user__user_id_736ebf7e_fk_authentic FOREIGN KEY (user_id) REFERENCES public.authentication_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: authentication_user_groups authentication_user_groups_group_id_6b5c44b7_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.authentication_user_groups
    ADD CONSTRAINT authentication_user_groups_group_id_6b5c44b7_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_admin_log django_admin_log_content_type_id_c4bce8eb_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_content_type_id_c4bce8eb_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_admin_log django_admin_log_user_id_c564eba6_fk_authentication_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_user_id_c564eba6_fk_authentication_user_id FOREIGN KEY (user_id) REFERENCES public.authentication_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: guardian_groupobjectpermission guardian_groupobject_content_type_id_7ade36b8_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.guardian_groupobjectpermission
    ADD CONSTRAINT guardian_groupobject_content_type_id_7ade36b8_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: guardian_groupobjectpermission guardian_groupobject_group_id_4bbbfb62_fk_auth_grou; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.guardian_groupobjectpermission
    ADD CONSTRAINT guardian_groupobject_group_id_4bbbfb62_fk_auth_grou FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: guardian_groupobjectpermission guardian_groupobject_permission_id_36572738_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.guardian_groupobjectpermission
    ADD CONSTRAINT guardian_groupobject_permission_id_36572738_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: guardian_userobjectpermission guardian_userobjectp_content_type_id_2e892405_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.guardian_userobjectpermission
    ADD CONSTRAINT guardian_userobjectp_content_type_id_2e892405_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: guardian_userobjectpermission guardian_userobjectp_permission_id_71807bfc_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.guardian_userobjectpermission
    ADD CONSTRAINT guardian_userobjectp_permission_id_71807bfc_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: guardian_userobjectpermission guardian_userobjectp_user_id_d5c1e964_fk_authentic; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.guardian_userobjectpermission
    ADD CONSTRAINT guardian_userobjectp_user_id_d5c1e964_fk_authentic FOREIGN KEY (user_id) REFERENCES public.authentication_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: listening_events listening_events_station_id_c913e7ee_fk_stations_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.listening_events
    ADD CONSTRAINT listening_events_station_id_c913e7ee_fk_stations_id FOREIGN KEY (station_id) REFERENCES public.stations(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: listening_events listening_events_user_id_3170c89a_fk_app_users_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.listening_events
    ADD CONSTRAINT listening_events_user_id_3170c89a_fk_app_users_id FOREIGN KEY (user_id) REFERENCES public.app_users(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: posts posts_station_id_2ce2b217_fk_stations_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.posts
    ADD CONSTRAINT posts_station_id_2ce2b217_fk_stations_id FOREIGN KEY (station_id) REFERENCES public.stations(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: reviews reviews_station_id_8b7ea576_fk_stations_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_station_id_8b7ea576_fk_stations_id FOREIGN KEY (station_id) REFERENCES public.stations(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: reviews reviews_user_id_c23b0903_fk_app_users_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_user_id_c23b0903_fk_app_users_id FOREIGN KEY (user_id) REFERENCES public.app_users(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: socialaccount_socialtoken socialaccount_social_account_id_951f210e_fk_socialacc; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.socialaccount_socialtoken
    ADD CONSTRAINT socialaccount_social_account_id_951f210e_fk_socialacc FOREIGN KEY (account_id) REFERENCES public.socialaccount_socialaccount(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: socialaccount_socialtoken socialaccount_social_app_id_636a42d7_fk_socialacc; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.socialaccount_socialtoken
    ADD CONSTRAINT socialaccount_social_app_id_636a42d7_fk_socialacc FOREIGN KEY (app_id) REFERENCES public.socialaccount_socialapp(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: socialaccount_socialaccount socialaccount_social_user_id_8146e70c_fk_authentic; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.socialaccount_socialaccount
    ADD CONSTRAINT socialaccount_social_user_id_8146e70c_fk_authentic FOREIGN KEY (user_id) REFERENCES public.authentication_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: songs songs_artist_id_cd88e06f_fk_artists_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.songs
    ADD CONSTRAINT songs_artist_id_cd88e06f_fk_artists_id FOREIGN KEY (artist_id) REFERENCES public.artists(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: station_streams station_streams_station_id_ed34a3f7_fk_stations_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.station_streams
    ADD CONSTRAINT station_streams_station_id_ed34a3f7_fk_stations_id FOREIGN KEY (station_id) REFERENCES public.stations(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: station_to_station_group station_to_station_group_group_id_8774970d_fk_station_groups_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.station_to_station_group
    ADD CONSTRAINT station_to_station_group_group_id_8774970d_fk_station_groups_id FOREIGN KEY (group_id) REFERENCES public.station_groups(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: station_to_station_group station_to_station_group_station_id_ec59ee7a_fk_stations_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.station_to_station_group
    ADD CONSTRAINT station_to_station_group_station_id_ec59ee7a_fk_stations_id FOREIGN KEY (station_id) REFERENCES public.stations(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: stations stations_latest_station_now_p_0be7a339_fk_stations_; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stations
    ADD CONSTRAINT stations_latest_station_now_p_0be7a339_fk_stations_ FOREIGN KEY (latest_station_now_playing_id) REFERENCES public.stations_now_playing(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: stations stations_latest_station_uptim_9ef73963_fk_stations_; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stations
    ADD CONSTRAINT stations_latest_station_uptim_9ef73963_fk_stations_ FOREIGN KEY (latest_station_uptime_id) REFERENCES public.stations_uptime(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: stations_metadata_fetch stations_metadata_fe_station_metadata_fet_654b6d10_fk_station_m; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stations_metadata_fetch
    ADD CONSTRAINT stations_metadata_fe_station_metadata_fet_654b6d10_fk_station_m FOREIGN KEY (station_metadata_fetch_category_id) REFERENCES public.station_metadata_fetch_categories(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: stations_metadata_fetch stations_metadata_fetch_station_id_3c1793db_fk_stations_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stations_metadata_fetch
    ADD CONSTRAINT stations_metadata_fetch_station_id_3c1793db_fk_stations_id FOREIGN KEY (station_id) REFERENCES public.stations(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: stations_now_playing stations_now_playing_song_id_29de6a79_fk_songs_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stations_now_playing
    ADD CONSTRAINT stations_now_playing_song_id_29de6a79_fk_songs_id FOREIGN KEY (song_id) REFERENCES public.songs(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: stations_now_playing stations_now_playing_station_id_85115440_fk_stations_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stations_now_playing
    ADD CONSTRAINT stations_now_playing_station_id_85115440_fk_stations_id FOREIGN KEY (station_id) REFERENCES public.stations(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: stations_uptime stations_uptime_station_id_7999418b_fk_stations_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stations_uptime
    ADD CONSTRAINT stations_uptime_station_id_7999418b_fk_stations_id FOREIGN KEY (station_id) REFERENCES public.stations(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: usersessions_usersession usersessions_userses_user_id_af5e0a6d_fk_authentic; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usersessions_usersession
    ADD CONSTRAINT usersessions_userses_user_id_af5e0a6d_fk_authentic FOREIGN KEY (user_id) REFERENCES public.authentication_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- PostgreSQL database dump complete
--

