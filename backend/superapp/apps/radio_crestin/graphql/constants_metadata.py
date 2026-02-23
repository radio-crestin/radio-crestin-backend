STATIONS_METADATA_GRAPHQL_QUERY = '''
query GetStationsMetadata($timestamp: Int, $changes_from_timestamp: Int) @cached(ttl: 0) {
  stations_metadata(timestamp: $timestamp, changes_from_timestamp: $changes_from_timestamp) {
    id
    slug
    title
    uptime {
      is_up
      latency_ms
      timestamp
    }
    now_playing {
      timestamp
      listeners
      song {
        id
        name
        thumbnail_url
        artist {
          id
          name
          thumbnail_url
        }
      }
    }
  }
}
'''

STATIONS_METADATA_HISTORY_GRAPHQL_QUERY = '''
query GetStationsMetadataHistory($station_slug: String!, $from_timestamp: Int, $to_timestamp: Int) @cached(ttl: 0) {
  stations_metadata_history(station_slug: $station_slug, from_timestamp: $from_timestamp, to_timestamp: $to_timestamp) {
    station_id
    station_slug
    station_title
    from_timestamp
    to_timestamp
    count
    history {
      timestamp
      listeners
      song {
        id
        name
        thumbnail_url
        artist {
          id
          name
          thumbnail_url
        }
      }
    }
  }
}
'''
