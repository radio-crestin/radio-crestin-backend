import {getStationsMetadata} from "../backendServices/stations";
import absoluteUrl from 'next-absolute-url'

function SiteMap() {
  // getServerSideProps will do the heavy lifting
}

// @ts-ignore
export async function getServerSideProps({ req, res }) {
  const { origin } = absoluteUrl(req)

  res.setHeader('Content-Type', 'text/plain');
  res.write(`# Allow all crawlers
User-agent: *
Allow: /

Sitemap: ${origin}/sitemap.xml
`);
  res.end();

  return {
    props: {},
  };
}

export default SiteMap;
