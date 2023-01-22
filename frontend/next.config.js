const nextRuntimeDotenv = require("next-runtime-dotenv");

const withConfig = nextRuntimeDotenv({
  path: '.env',
  public: [],
  server: [],
});

const config = withConfig({
  reactStrictMode: true,
  output: 'standalone',
  images: {
    formats: ['image/avif', 'image/webp'],
    domains: [
      'radio-crestin.s3.amazonaws.com',
      'cdn.pictures.aripisprecer.ro',
      'pictures.aripisprecer.ro',
    ],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384, 480, 640],
    minimumCacheTTL: 60 * 60 * 24,
  },
  env: {
    cdnPrefix:
      process.env.FRONTEND_CDN_PREFIX !== ''
        ? process.env.FRONTEND_CDN_PREFIX
        : '',
    REFRESH_CACHE_TOKEN: process.env.FRONTEND_REFRESH_CACHE_TOKEN,
  },
  // Use the CDN in production and localhost for development.
  assetPrefix:
    process.env.FRONTEND_CDN_PREFIX !== ''
      ? process.env.FRONTEND_CDN_PREFIX
      : undefined,
  compiler: {
    removeConsole: process.env.NODE_ENV === 'development' ? false : {
      exclude: ['error'],
    },
  },
});
console.log('process.env.FRONTEND_CDN_PREFIX', process.env.FRONTEND_CDN_PREFIX);

if (process.env.ANALYZE === 'true') {
  console.log('ANALYZE is enabled.');
  const withBundleAnalyzer = require('@next/bundle-analyzer')({
    enabled: process.env.ANALYZE === 'true',
  });
  module.exports = withBundleAnalyzer(config);
} else {
  module.exports = config;
}
