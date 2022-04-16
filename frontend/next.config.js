const nextRuntimeDotenv = require("next-runtime-dotenv");
const {PROJECT_ENV} = require("./utils/env");

const withConfig = nextRuntimeDotenv({
  path: ".env",
  public: [],
  server: [],
});

module.exports = withConfig({
  experimental: {
    outputStandalone: true,
  },
  // Use the CDN in production and localhost for development.
  assetPrefix: PROJECT_ENV.FRONTEND_CDN_PREFIX !== "" ?  PROJECT_ENV.FRONTEND_CDN_PREFIX : '',
});
