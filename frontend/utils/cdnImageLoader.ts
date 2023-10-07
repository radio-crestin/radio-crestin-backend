const allowedCDNs = [
  'radio-crestin.s3.amazonaws.com',
  'cdn.pictures.aripisprecer.ro',
  'pictures.aripisprecer.ro',
  'images.radio.co',
];

export const cdnImageLoader = ({src, width, quality = 80}: any) => {
  if(process.env.FRONTEND_CDN_IMAGE_PREFIX && allowedCDNs.some(element => src.includes(element))) {
    return `${
      process.env.FRONTEND_CDN_IMAGE_PREFIX
    }/_next/image?w=${width}&q=${quality}&url=${encodeURI(src)}`;
  }
  return src;
};
