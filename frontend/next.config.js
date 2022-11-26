const nextRuntimeDotenv = require("next-runtime-dotenv");

const withConfig = nextRuntimeDotenv({
  path: ".env",
  public: [],
  server: []
});
const withBundleAnalyzer = require("@next/bundle-analyzer")({
  enabled: process.env.ANALYZE === "true",
})

module.exports = withConfig(withBundleAnalyzer({
  reactStrictMode: false,
  output: 'standalone',
  images: {
    formats: ['image/avif', 'image/webp'],
    domains: ['radio-crestin.s3.amazonaws.com', 'cdn.pictures.aripisprecer.ro', 'pictures.aripisprecer.ro'],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384, 480, 640],
    minimumCacheTTL: 60 * 60 * 24,
  },
  env: {
    cdnPrefix: process.env.FRONTEND_CDN_PREFIX !== "" ?  process.env.FRONTEND_CDN_PREFIX : ''
  },
  experimental: {
    nextScriptWorkers: true,
  },
  // Use the CDN in production and localhost for development.
  // assetPrefix: process.env.FRONTEND_CDN_PREFIX !== "" ?  process.env.FRONTEND_CDN_PREFIX : undefined,
}));
console.log("process.env.FRONTEND_CDN_PREFIX", process.env.FRONTEND_CDN_PREFIX)
