import axios, { AxiosRequestConfig } from "axios";
import { StationsMetadata } from "../types";
import { PROJECT_ENV } from "../utils/env";

export const getStationsMetadata = (): Promise<StationsMetadata> => {
  const options: AxiosRequestConfig = {
    method: "POST",
    url: PROJECT_ENV.FRONTEND_GRAPHQL_INTERNAL_ENDPOINT_URI,
    headers: {
      "content-type": "application/json",
    },
    data: {
      operationName: "GetStations",
      query: `
query GetStations {
  station_groups {
    id
    name
    order
    station_to_station_groups {
      station_id
      order
    }
  }
  stations {
    id
    order
    title
    website
    email
    stream_url
    thumbnail_url
    radio_crestin_listeners
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
