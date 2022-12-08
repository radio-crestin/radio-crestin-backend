import React, {useEffect} from 'react';
import {useToast} from '@chakra-ui/react';
import {getStationsMetadata} from '../backendServices/stations';
import {StationsMetadata} from '../types';
import StationPage from './[station_category_slug]/[station_slug]';
import {seoInternalErrorPage} from '@/utils/seo';

export default function InternalErrorPage({
  stations_metadata,
}: {
  stations_metadata: StationsMetadata;
}) {
  const toast = useToast();

  useEffect(() => {
    toast({
      title: 'A apărut o eroare neașteptată.',
      description: 'Vă rugăm să încercați mai târziu!',
      status: 'error',
      position: 'top',
      duration: 3000,
      isClosable: true,
    });
  }, []);

  return StationPage({
    stations_metadata,
    seoMetadata: seoInternalErrorPage,
  });
}

export async function getStaticProps(context: any) {
  const stations_metadata = await getStationsMetadata();

  return {
    props: {
      stations_metadata,
    },
    revalidate: 10,
  };
}
