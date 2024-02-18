import { config } from "dotenv";
import path from "path";

config({ path: path.resolve(__dirname, "../.env") });

export const PROJECT_ENV: {
  AUTH_DEBUG: boolean;
  AUTH_SERVER_PORT: number;
  AUTH_GRAPHQL_ENDPOINT_URI: string;
  AUTH_GRAPHQL_ADMIN_SECRET: string;
} = {
  AUTH_DEBUG: process.env.AUTH_DEBUG === "true",
  AUTH_SERVER_PORT: parseInt(process.env.AUTH_SERVER_PORT || "8080"),
  AUTH_GRAPHQL_ENDPOINT_URI: process.env.AUTH_GRAPHQL_ENDPOINT_URI || "",
  AUTH_GRAPHQL_ADMIN_SECRET: process.env.AUTH_GRAPHQL_ADMIN_SECRET || "",
};
