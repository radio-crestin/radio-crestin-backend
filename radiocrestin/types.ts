export interface Stats {
  timestamp: string
  current_song: string | null
  listeners: string | null
}

export interface StreamStatus {
  up: boolean
  latencyMs: number
  rawData: any
}

export interface StationStats {
  rawData: any
  stats: Stats
  error?: any | null
  streamStatus?: StreamStatus | null
}

export interface StationStatsByStationId {
  [key: number]: StationStats
}

interface BaseStation {
  id: number,
  title: string,
  website: string,
  contact: string,
  stream_url: string,
}

export interface Station extends BaseStation {

  // Metadata endpoints
  shoutcast_stats_url?: string
  old_icecast_html_stats_url?: string
  icecast_stats_url?: string
  radio_co_stats_url?: string
  shoutcast_xml_stats_url?: string
  old_shoutcast_stats_html_url?: string

}

export interface StationData extends BaseStation {
  stats: Stats
}
