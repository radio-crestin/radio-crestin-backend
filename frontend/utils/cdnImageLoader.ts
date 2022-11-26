export const cdnImageLoader = ({ src, width, quality }: any) => {
  return `/_next/image?w=${width}&q=${quality || 85}&url=${encodeURI(src)}`
}
