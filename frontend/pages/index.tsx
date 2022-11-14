import React from 'react';
import {getStationsMetadata} from '../backendServices/stations';
import {StationsMetadata} from '../types';
import StationPage from './[station_category_slug]/[station_slug]';
import {seoHomepage} from '@/utils/seo';

export default function Home({
  stations_metadata,
}: {
  stations_metadata: StationsMetadata;
}) {
  return StationPage({
    stations_metadata,
    seoMetadata: seoHomepage,
  });
}

export async function getServerSideProps() {
  const stations_metadata = await getStationsMetadata();
  return {
    props: {
      stations_metadata,
    },
  };
}
