export const cdnImageLoader = ({ src, width, quality }: any) => {
  return `${process.env.cdnPrefix}/_next/image?url=${src}&w=${width}&q=${quality || 75}`
}
