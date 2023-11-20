import { config } from "dotenv";
import path from "path";

config({ path: path.resolve(__dirname, "../.env") });

export const PROJECT_ENV: {
  APP_DEBUG: boolean;
  APP_SERVER_PORT: number;
  APP_GRAPHQL_ENDPOINT_URI: string;
  APP_GRAPHQL_ADMIN_SECRET: string;
  APP_REFRESH_STATIONS_METADATA_CRON: string;
  APP_REFRESH_STATIONS_RSS_FEED_CRON: string;
  SOCKS5_RETRY_PROXY: string;
} = {
  APP_DEBUG: process.env.APP_DEBUG === "true",
  APP_SERVER_PORT: parseInt(process.env.APP_SERVER_PORT || "8080"),
  APP_GRAPHQL_ENDPOINT_URI: process.env.APP_GRAPHQL_ENDPOINT_URI || "",
  APP_GRAPHQL_ADMIN_SECRET: process.env.APP_GRAPHQL_ADMIN_SECRET || "",
  APP_REFRESH_STATIONS_METADATA_CRON:
    process.env.APP_REFRESH_STATIONS_METADATA_CRON || "",
  APP_REFRESH_STATIONS_RSS_FEED_CRON:
    process.env.APP_REFRESH_STATIONS_RSS_FEED_CRON || "",
  SOCKS5_RETRY_PROXY: process.env.SOCKS5_RETRY_PROXY || "tor-proxy:9050",
};
