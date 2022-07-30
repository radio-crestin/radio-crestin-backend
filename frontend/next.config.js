const nextRuntimeDotenv = require("next-runtime-dotenv");

const withConfig = nextRuntimeDotenv({
  path: ".env",
  public: [],
  server: []
});

module.exports = withConfig({
  reactStrictMode: false,
  images: {
    formats: ['image/avif', 'image/webp'],
    domains: ['radio-crestin.s3.amazonaws.com', '*.aripisprecer.ro'],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384, 480, 640]
  },
  env: {
    cdnPrefix: process.env.FRONTEND_CDN_PREFIX !== "" ?  process.env.FRONTEND_CDN_PREFIX : ''
  },
  experimental: {
    outputStandalone: true
  },
  // Use the CDN in production and localhost for development.
  assetPrefix: process.env.FRONTEND_CDN_PREFIX !== "" ?  process.env.FRONTEND_CDN_PREFIX : '',
});
console.log("process.env.FRONTEND_CDN_PREFIX", process.env.FRONTEND_CDN_PREFIX);
