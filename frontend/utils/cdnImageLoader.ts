export const cdnImageLoader = ({src, width, quality = 80}: any) => {
  return `${
    process.env.cdnPrefix
  }/_next/image?w=${width}&q=${quality}&url=${encodeURI(src)}`;
};
