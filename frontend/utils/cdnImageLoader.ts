const allowedCDNs = [
  'radio-crestin.s3.amazonaws.com',
  'cdn.pictures.aripisprecer.ro',
  'pictures.aripisprecer.ro',
  'images.radio.co',
];

export const cdnImageLoader = ({src, width, quality = 80}: any) => {
  if(process.env.cdnPrefix && allowedCDNs.some(element => src.includes(element))) {
    return `${
      process.env.cdnPrefix
    }/_next/image?w=${width}&q=${quality}&url=${encodeURI(src)}`;
  }
  return src;
};
