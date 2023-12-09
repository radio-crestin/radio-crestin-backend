import { Station, StationRssFeed } from "../types";
import { read as rssReader } from "feed-reader";
import { Promise as BluebirdPromise } from "bluebird";
import axios, { AxiosRequestConfig } from "axios";
import { PROJECT_ENV } from "../env";
import { getStations } from "../services/getStations";
import { Logger } from "tslog";

const logger: Logger<any> = new Logger({ name: "stationRssFeedScrape", minLevel: PROJECT_ENV.APP_DEBUG? 2:3 });

const getStationRssFeed = ({
  station,
}: {
  station: Station;
}): Promise<StationRssFeed> => {
  if (typeof station.rss_feed === "string" && !!station.rss_feed) {
    return rssReader(station.rss_feed).then((feed) => {
      return {
        posts: feed?.entries?.map((e: any) => {
          return {
            title: e.title,
            link: e.link,
            description: e.description,
            published: e.published,
          };
        }),
      };
    });
  }

  return Promise.resolve({
    posts: [],
  });
};

const updateStationPosts = async ({
  station,
  stationRssFeed,
}: {
  station: Station;
  stationRssFeed: StationRssFeed;
}): Promise<boolean> => {
  if (stationRssFeed && stationRssFeed?.posts?.length == 0) {
    return Promise.resolve(true);
  }

  const options: AxiosRequestConfig = {
    method: "POST",
    url: PROJECT_ENV.APP_GRAPHQL_ENDPOINT_URI,
    headers: {
      "content-type": "application/json",
      "x-hasura-admin-secret": PROJECT_ENV.APP_GRAPHQL_ADMIN_SECRET,
    },
    timeout: 10000,
    data: {
      operationName: "UpdateStationPosts",
      query: `mutation UpdateStationPosts($objects: [posts_insert_input!]!) {
  insert_posts(
    objects: $objects
    on_conflict: {
      constraint: posts_station_id_link_key
      update_columns: [description, title, published]
    }
  ) {
    affected_rows
  }
}
`,
      variables: {
        objects: stationRssFeed?.posts?.map((rssFeedPost) => {
          return {
            station_id: station.id,
            title: rssFeedPost.title,
            description: rssFeedPost.description,
            link: rssFeedPost.link,
            published: rssFeedPost.published,
          };
        }),
      },
    },
  };

  return axios.request(options).then(function (response) {
    if (!response.data) {
      throw new Error(
        `Invalid response ${response.status}: ${JSON.stringify(response.data)}`
      );
    }

    if (response.data.errors) {
      throw new Error(
        `Invalid response ${response.status}: ${JSON.stringify(response.data)}`
      );
    }

    return (
      typeof response.data?.data?.insert_posts?.affected_rows !== "undefined"
    );
  });
};

export const refreshStationsRssFeed = async () => {
  logger.info("Running refreshStationsRssFeed...");

  const stations: Station[] = await getStations();

  return BluebirdPromise.map(
    stations.sort(() => 0.5 - Math.random()),
    async (station: Station) => {
      const stationRssFeed = await getStationRssFeed({ station });

      const done = await updateStationPosts({ station, stationRssFeed });

      return {
        stationId: station.id,
        done: done,
      };
    },
    {
      concurrency: 1,
    }
  );
};
