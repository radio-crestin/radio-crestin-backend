import { Station, StationRssFeed } from "../types";
import { read as rssReader } from "feed-reader";
import { Promise as BluebirdPromise } from "bluebird";
import axios, { AxiosRequestConfig } from "axios";
import https from "https";
import { PROJECT_ENV } from "../env";
import { getStations } from "../services/getStations";
import { Logger } from "tslog";

// Create an https agent that doesn't verify certificates
const httpsAgent = new https.Agent({
  rejectUnauthorized: false
});

const logger: Logger<any> = new Logger({ name: "stationRssFeedScrape", minLevel: PROJECT_ENV.APP_DEBUG? 2:3 });

// Custom RSS reader function that ignores certificate errors
const secureRssReader = (url: string) => {
  // The feed-reader package uses axios internally, so we need to patch axios globally
  // just for this call to ignore certificate errors
  const originalCreate = axios.create;
  axios.create = function(...args) {
    const instance = originalCreate.apply(this, args);
    instance.defaults.httpsAgent = httpsAgent;
    return instance;
  };
  
  // Call the original rssReader
  return rssReader(url).then((feed) => {
    // Restore the original axios.create
    axios.create = originalCreate;
    return feed;
  }).catch((error) => {
    // Restore the original axios.create even if there's an error
    axios.create = originalCreate;
    throw error;
  });
};

const getStationRssFeed = ({
  station,
}: {
  station: Station;
}): Promise<StationRssFeed> => {
  if (typeof station.rss_feed === "string" && !!station.rss_feed) {
    return secureRssReader(station.rss_feed).then((feed) => {
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
    httpsAgent, // Use the agent that doesn't verify certificates
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
