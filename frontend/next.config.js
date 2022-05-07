const nextRuntimeDotenv = require("next-runtime-dotenv");

const withConfig = nextRuntimeDotenv({
  path: ".env",
  public: [],
  server: []
});

module.exports = withConfig({
  reactStrictMode: false,
  experimental: {
    outputStandalone: true
  },
  // Use the CDN in production and localhost for development.
  assetPrefix: process.env.FRONTEND_CDN_PREFIX !== "" ?  process.env.FRONTEND_CDN_PREFIX : '',
});
console.log("process.env.FRONTEND_CDN_PREFIX", process.env.FRONTEND_CDN_PREFIX);
