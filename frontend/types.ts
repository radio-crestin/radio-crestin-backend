export interface Song {
  id: number;
  name: string;
  artist: Artist;
}

export interface Artist {
  id: number;
  name: string;
}

export interface StationNowPlaying {
  id: number;
  timestamp: string;
  listeners: number | null;
  song: Song | null;
}

export interface StationUptime {
  is_up?: boolean;
  latencyMs?: number;
  statusMessage?: string;
  rawData?: any;
}

export interface Station {
  id: string;
  order: number;
  title: string;
  website: string;
  email: string;
  stream_url: string;
  thumbnail_url: string;
  station_to_station_groups: { group_id: number }[];

  uptime?: StationUptime;
  now_playing?: StationNowPlaying;
}

export interface StationGroup {
  id: number;
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
  user_name: String,
  ip_address: String,
  session_id: String,
  station_id: bigint,
  stars: bigint,
  message: String,
}

export interface ListeningEvent {
  ip_address: String,
  session_id: String,
  station_id: bigint,
  info: any,
}

