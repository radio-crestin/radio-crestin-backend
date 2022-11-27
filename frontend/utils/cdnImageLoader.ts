export const cdnImageLoader = ({ src, width, quality }: any) => {
  return `${process.env.cdnPrefix}/_next/image?w=${width}&q=${quality || 85}&url=${encodeURI(src)}`
}
