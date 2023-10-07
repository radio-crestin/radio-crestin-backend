const nextRuntimeDotenv = require('next-runtime-dotenv');

const withConfig = nextRuntimeDotenv({
  path: '.env',
  public: [],
  server: [],
});


const allowedCDNs = [
  'radio-crestin.s3.amazonaws.com',
  'cdn.pictures.aripisprecer.ro',
  'pictures.aripisprecer.ro',
  'images.radio.co',
];

const config = withConfig({
  reactStrictMode: true,
  output: 'standalone',
  images: {
    formats: ['image/webp'],
    domains: allowedCDNs,
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384, 480, 640],
    minimumCacheTTL: 60 * 60 * 24,
  },
  env: {
    cdnPrefix:
      process.env.FRONTEND_CDN_IMAGE_PREFIX !== ''
        ? process.env.FRONTEND_CDN_IMAGE_PREFIX
        : '',
  },
  // Use the CDN in production and localhost for development.
  assetPrefix:
    process.env.FRONTEND_CDN_IMAGE_PREFIX !== ''
      ? process.env.FRONTEND_CDN_IMAGE_PREFIX
      : undefined,
  compiler: {
    removeConsole:
      process.env.NODE_ENV === 'development'
        ? false
        : {
            exclude: ['error'],
          },
  },
});
console.log('process.env.FRONTEND_CDN_IMAGE_PREFIX', process.env.FRONTEND_CDN_IMAGE_PREFIX);

if (process.env.ANALYZE === 'true') {
  console.log('ANALYZE is enabled.');
  const withBundleAnalyzer = require('@next/bundle-analyzer')({
    enabled: process.env.ANALYZE === 'true',
  });
  module.exports = {
    ...withBundleAnalyzer(config),
  };
} else {
  module.exports = config;
}
