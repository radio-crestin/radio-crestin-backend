import React from 'react';
import {StationsMetadata} from '../../types';
import {getStationsMetadata} from '../../backendServices/stations';
import StationPage from './[station_slug]';
import {seoCategory} from '@/utils/seo';

export default function StationCategoryPage({
  stations_metadata,
  station_category_slug,
}: {
  stations_metadata: StationsMetadata;
  station_category_slug: string;
}) {
  return StationPage({
    stations_metadata,
    station_category_slug,
    seoMetadata: seoCategory(station_category_slug),
  });
}

export async function getServerSideProps(context: any) {
  context.res.setHeader(
    'Cache-Control',
    'public, s-maxage=10, stale-while-revalidate=59',
  );
  const stations_metadata = await getStationsMetadata();
  const {station_category_slug} = context.query;

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
  };
}
