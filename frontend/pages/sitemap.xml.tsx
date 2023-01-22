import {getStationsMetadata} from '../backendServices/stations';

function generateSiteMap(urls: string[]) {
  return `<?xml version="1.0" encoding="UTF-8"?>
     <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
     ${urls
    .map(url => {
      return `
       <url>
           <loc>${url}</loc>
       </url>
     `;
    })
    .join('')}
   </urlset>
 `;
}

function SiteMap() {
  // getServerSideProps will do the heavy lifting
}

export const getAllUrls = async (include_api_endpoints = false) => {
  const origin = 'https://www.radio-crestin.com';
  const stations_metadata = await getStationsMetadata();
  const urls: string[] = [];
  urls.push(`${origin}/`);
  for (const station_group of stations_metadata.station_groups) {
    for (const station_relationship of station_group.station_to_station_groups) {
      const station = stations_metadata.stations.find(
        s => s.id === station_relationship.station_id,
      );
      if (station) {
        urls.push(`${origin}/${station_group.slug}/${station.slug}`);
      }
    }
  }
  return urls;
}

// @ts-ignore
export async function getServerSideProps(context) {
  context.res.setHeader(
    'Cache-Control',
    'public, s-maxage=10, stale-while-revalidate=59',
  );

  const urls = await getAllUrls();
  // We generate the XML sitemap with the posts data
  const sitemap = generateSiteMap(urls);

  context.res.setHeader('Content-Type', 'text/xml');
  // we send the XML to the browser
  context.res.write(sitemap);
  context.res.end();

  return {
    props: {},
  };
}

export default SiteMap;
