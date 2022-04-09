export interface StationMetadataFetcherCategory {
    slug: string
}

export interface StationMetadataFetcher {
    url: string
    station_metadata_fetch_category: StationMetadataFetcherCategory
}

export interface Song {
    name: string
    artist: string
}

export interface StationNowPlaying {
    timestamp?: string
    current_song?: Song | null
    listeners?: number | null
    raw_data?: any
    error?: any | null
}

export interface StationUptime {
    timestamp: string
    is_up: boolean
    latency_ms: number
    raw_data: any
}

export interface Station {
    id: number
    title: string
    stream_url: string
    station_metadata_fetches: StationMetadataFetcher[]
}