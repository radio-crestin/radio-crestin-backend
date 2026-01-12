# GraphQL query constants

STATIONS_GRAPHQL_QUERY = '''
query GetStations @cache_control(max_age: 30, max_stale: 30, stale_while_revalidate: 30) @cached(ttl: 0) {
  __typename
  stations(order_by: {order: asc, title: asc}) {
    __typename
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
    station_streams {
      __typename
      order
      type
      stream_url
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
    }
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
'''

REVIEWS_GRAPHQL_QUERY = '''
query GetReviews($station_id: Int) @cache_control(max_age: 30, max_stale: 30, stale_while_revalidate: 30) @cached(ttl: 0) {
  __typename
  reviews(station_id: $station_id) {
    __typename
    id
    station_id
    stars
    message
    created_at
    updated_at
  }
}
'''
