# GraphQL query constants

# Station field selection shared by the public /api/v1/stations and the
# per-device /api/v1/private-stations endpoints, so both return identically
# shaped station objects under data.stations.
STATION_FIELDS_BLOCK = '''    __typename
    id
    slug
    order
    title
    website
    slug
    email
    stream_url
    proxy_stream_url
    hls_stream_url
    thumbnail_url
    total_listeners
    radio_crestin_listeners
    description
    description_action_title
    description_link
    feature_latest_post
    facebook_page_id
    station_type
    station_streams {
      __typename
      order
      type
      stream_url
    }
    playlist_items {
      __typename
      id
      order
      type
      url
      title
      thumbnail_url
      duration_seconds
    }
    posts(limit: 1, order_by: {published: desc}) {
      __typename
      id
      title
      description
      link
      published
    }
    uptime {
      __typename
      is_up
      latency_ms
      timestamp
    }
    now_playing {
      __typename
      id
      timestamp
      song {
        __typename
        id
        name
        thumbnail_url
        artist {
          __typename
          id
          name
          thumbnail_url
        }
      }
    }
    reviews {
      __typename
      id
      stars
      message
      created_at
      updated_at
    }
    reviews_stats {
      __typename
      number_of_reviews
      average_rating
    }'''

STATIONS_GRAPHQL_QUERY = '''
query GetStations($station_slugs: [String!], $exclude_station_slugs: [String!]) @cache_control(max_age: 30, max_stale: 30, stale_while_revalidate: 30) @cached(ttl: 0) {
  __typename
  stations(order_by: {order: asc, title: asc}, station_slugs: $station_slugs, exclude_station_slugs: $exclude_station_slugs) {
%s
  }
  station_groups {
    __typename
    id
    name
    order
    slug
    station_to_station_groups {
      __typename
      station_id
      order
    }
  }
}
''' % (STATION_FIELDS_BLOCK,)

# Aliased to `stations` so clients parse data.stations exactly like the
# public stations endpoint. No station_groups block: private stations simply
# merge into the clients' existing lists.
PRIVATE_STATIONS_GRAPHQL_QUERY = '''
query GetPrivateStations($device_id: String!) @cached(ttl: 0) {
  __typename
  stations: private_stations(device_id: $device_id) {
%s
  }
}
''' % (STATION_FIELDS_BLOCK,)

# Uses playlist_stations (not stations) so private playlist stations keep
# live-syncing on allowlisted devices: the resolver requires exact slugs and
# intentionally skips the is_public filter. Aliased to `stations` to keep the
# response shape unchanged.
STATION_PLAYLIST_GRAPHQL_QUERY = '''
query GetStationPlaylist($station_slugs: [String!]) @cached(ttl: 0) {
  stations: playlist_stations(station_slugs: $station_slugs) {
    id
    slug
    station_type
    playlist_items {
      id
      order
      type
      url
      title
      thumbnail_url
      duration_seconds
    }
  }
}
'''

REVIEWS_GRAPHQL_QUERY = '''
query GetReviews($station_id: Int, $station_slug: String) @cache_control(max_age: 30, max_stale: 30, stale_while_revalidate: 30) @cached(ttl: 0) {
  __typename
  reviews(station_id: $station_id, station_slug: $station_slug) {
    __typename
    id
    station_id
    song_id
    stars
    message
    created_at
    updated_at
  }
}
'''
