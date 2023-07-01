export interface Song {
  id: number;
  name: string | null;
  thumbnail_url: string | null;
  artist: Artist;
}

export interface Artist {
  id: number;
  name: string | null;
  thumbnail_url: string | null;
}

export interface StationNowPlaying {
  id: number;
  timestamp: string;
  song: Song | null;
}

export interface StationUptime {
  is_up?: boolean;
  latencyMs?: number;
  statusMessage?: string;
  rawData?: any;
}

export interface Post {
  id: number;
  title: string;
  description: string;
  link: string;
  published: string;
}

export interface StationReview {
  id: number;
  stars: number;
  message: string | null;
}

// TODO: update the below types with the added fields
export interface Station {
  id: number;
  slug: string;
  order: number;
  title: string;
  website: string | null;
  email: string | null;
  stream_url: string;
  proxy_stream_url: string;
  hls_stream_url: string;
  thumbnail_url: string | null;
  total_listeners: number;
  description: string | null;
  description_action_title: string | null;
  description_link: string | null;
  feature_latest_post: boolean;
  facebook_page_id: string | null;

  posts: Post[];
  uptime?: StationUptime;
  now_playing?: StationNowPlaying;
  reviews: StationReview[];
}

export interface StationGroup {
  id: number;
  slug: string;
  name: string;
  order: number;
  station_to_station_groups: {
    station_id: number;
  }[];
}

export interface StationsMetadata {
  station_groups: StationGroup[];
  stations: Station[];
}

export interface Review {
  user_name: String | null;
  ip_address: String;
  session_id: String;
  station_id: bigint;
  stars: number;
  message: String | null;
}

export interface ClientSideReview {
  user_name: String | null;
  station_id: bigint;
  stars: number;
  message: String | null;
}

export interface ListeningEvent {
  ip_address: String | null;
  session_id: String;
  station_id: bigint;
  info: any;
}

export interface ClientSideListeningEvent {
  station_id: bigint;
  info: any;
}

export interface SeoMetadata {
  title: string;
  description?: string;
  keywords?: string;
}
