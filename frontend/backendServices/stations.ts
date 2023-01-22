import {StationsMetadata} from '../types';
import {PROJECT_ENV} from '@/utils/env';

const cachios = require('cachios');

export const getStationsMetadata = (): Promise<StationsMetadata> => {
  return cachios.post(
    PROJECT_ENV.FRONTEND_GRAPHQL_INTERNAL_ENDPOINT_URI,
    {
      operationName: 'GetStations',
      query: `
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
    radio_crestin_listeners
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

    `,
      variables: {},
    },
    {
      headers: {
        'content-type': 'application/json',
      },
      ttl: 5,
    }
  ).then(function (response: any) {
    if (!response.data?.data) {
      throw new Error(`Invalid response: ${JSON.stringify(response.data)}`);
    }

    return {
      station_groups: response.data.data.station_groups,
      stations: response.data.data.stations,
    };
  });
};
