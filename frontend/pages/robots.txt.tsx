function SiteMap() {
  // getServerSideProps will do the heavy lifting
}

// @ts-ignore
export async function getServerSideProps(context: any) {
  context.res.setHeader(
    'Cache-Control',
    'public, s-maxage=10, stale-while-revalidate=59',
  );
  const origin = 'https://www.radio-crestin.com';

  context.res.setHeader('Content-Type', 'text/plain');
  context.res.write(`# Allow all crawlers
User-agent: *
Allow: /

Sitemap: ${origin}/sitemap.xml
`);
  context.res.end();

  return {
    props: {},
  };
}

export default SiteMap;
