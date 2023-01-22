import React from 'react';
import {StationsMetadata} from '../../types';
import {getStationsMetadata} from '../../backendServices/stations';
import StationPage from './[station_slug]';
import {seoCategory} from '@/utils/seo';

export default function StationCategoryPage({
                                              stations_metadata,
                                              station_category_slug,
                                              fullURL,
                                            }: {
  stations_metadata: StationsMetadata;
  station_category_slug: string;
  fullURL: string;
}) {
  return StationPage({
    stations_metadata,
    station_category_slug,
    seoMetadata: seoCategory(station_category_slug),
    fullURL: fullURL,
  });
}
//
// export async function getServerSideProps(context: any) {
//   const {req, res, query} = context;
//   res.setHeader(
//     'Cache-Control',
//     'public, s-maxage=10, stale-while-revalidate=59',
//   );
//   const stations_metadata = await getStationsMetadata();
//   const {station_category_slug} = query;
//   const {pathname} = parse(req.url, true);
//   const host = req.headers.host;
//
//   const stationData = stations_metadata.station_groups.find(
//     group => group.slug === station_category_slug,
//   );
//
//   if (!stationData) {
//     return {
//       redirect: {
//         permanent: false,
//         destination: `/?error=Categoria ${station_category_slug} nu a fost gasita`,
//       },
//     };
//   }
//
//   return {
//     props: {
//       stations_metadata,
//       station_category_slug,
//       fullURL: `https://www.${host}${pathname}`,
//     },
//   };
// }

export async function getStaticProps(context: any) {
  const {params} = context;
  const stations_metadata = await getStationsMetadata();
  const {station_category_slug} = params;

  const stationData = stations_metadata.station_groups.find(
    group => group.slug === station_category_slug,
  );

  if (!stationData) {
    return {
      redirect: {
        permanent: false,
        destination: `/?error=Categoria ${station_category_slug} nu a fost gasita`,
      },
    };
  }

  return {
    props: {
      stations_metadata,
      station_category_slug,
    },
    revalidate: 10,
  };
}

export async function getStaticPaths() {
  const stations_metadata = await getStationsMetadata();

  // Generate paths with all statinos for each station group
  const paths = stations_metadata.station_groups.map(station_group => {
    return {
      params: {
        station_category_slug: station_group.slug,
      },
    };
  });

  // We'll pre-render only these paths at build time.
  // { fallback: blocking } will server-render pages
  // on-demand if the path doesn't exist.
  return {paths, fallback: 'blocking'}
}
