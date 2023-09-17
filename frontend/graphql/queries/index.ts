import {gql} from '@apollo/client';

export const getStationsQuery = gql`
  query GetStations {
    stations(order_by: {order: asc}) {
      id
      slug
      order
      title
      website
      email
      stream_url
      proxy_stream_url
      hls_stream_url
      thumbnail_url
      total_listeners
      description
      description_action_title
      description_link
      feature_latest_post
      facebook_page_id
      posts(limit: 1, order_by: {published: desc}) {
        id
        title
        description
        link
        published
      }
      uptime {
        is_up
        latency_ms
        timestamp
      }
      now_playing {
        id
        timestamp
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
      reviews {
        id
        stars
        message
      }
    }
    station_groups(order_by: {order: asc}) {
      id
      slug
      name
      order
      station_to_station_groups {
        station_id
        order
      }
    }
  }
`;
