function SiteMap() {
  // getServerSideProps will do the heavy lifting
}

// @ts-ignore
export async function getServerSideProps({ res }) {
  const origin = "https://www.radio-crestin.com";

  res.setHeader("Content-Type", "text/plain");
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
