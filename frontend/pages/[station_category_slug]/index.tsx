import React from 'react';
import {StationsMetadata} from '../../types';
import {getStationsMetadata} from '../../backendServices/stations';
import StationPage from './[station_slug]';

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
  });
}

export async function getServerSideProps(context: any) {
  const stations_metadata = await getStationsMetadata();
  const {station_category_slug} = context.query;

  return {
    props: {
      stations_metadata,
      station_category_slug,
    },
  };
}
