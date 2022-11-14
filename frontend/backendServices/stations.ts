import axios, {AxiosRequestConfig} from 'axios';
import {StationsMetadata} from '../types';
import {PROJECT_ENV} from '@/utils/env';

export const getStationsMetadata = (): Promise<StationsMetadata> => {
  const options: AxiosRequestConfig = {
    method: 'POST',
    url: PROJECT_ENV.FRONTEND_GRAPHQL_INTERNAL_ENDPOINT_URI,
    headers: {
      'content-type': 'application/json',
    },
    data: {
      operationName: 'GetStations',
      query: `
query GetStations {
  stations {
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
  station_groups {
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
  };

  return axios.request(options).then(function (response) {
    if (!response.data?.data) {
      throw new Error(`Invalid response: ${JSON.stringify(response.data)}`);
    }

    return {
      station_groups: response.data.data.station_groups,
      stations: response.data.data.stations,
    };
  });
};
