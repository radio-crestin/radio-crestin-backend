import {Station} from "@/types";
import axios, {AxiosRequestConfig} from "axios";
import {PROJECT_ENV} from "@/env";

export const getStations = (): Promise<Station[]> => {
    const options: AxiosRequestConfig = {
        method: "POST",
        url: PROJECT_ENV.APP_GRAPHQL_ENDPOINT_URI,
        headers: {
            "content-type": "application/json",
            "x-hasura-admin-secret": PROJECT_ENV.APP_GRAPHQL_ADMIN_SECRET,
        },
        data: {
            operationName: "GetStations",
            query: `query GetStations {
  stations {
    id
    title
    stream_url
    rss_feed
    station_metadata_fetches {
      station_metadata_fetch_category {
        slug
      }
      url
    }
  }
}`,
            variables: {},
        },
    };

    return axios.request(options).then(function (response) {
        if (!response.data?.data) {
            throw new Error(`Invalid response: ${JSON.stringify(response.data)}`);
        }

        return response.data.data.stations as Station[];

    });
};