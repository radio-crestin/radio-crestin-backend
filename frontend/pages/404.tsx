import {useRouter} from 'next/router';
import React, {useEffect} from 'react';
import {useToast} from '@chakra-ui/react';
import {getStationsMetadata} from '../backendServices/stations';
import {StationsMetadata} from '../types';
import StationPage from './[station_category_slug]/[station_slug]';
import {seoHomepage} from '@/utils/seo';

export default function NotFoundPage({
  stations_metadata,
}: {
  stations_metadata: StationsMetadata;
}) {
  const router = useRouter();
  const toast = useToast();

  useEffect(() => {
    toast({
      title: `Eroare!`,
      description: (
        <>
          Statia <b>{router.asPath}</b> nu exista !
        </>
      ),
      status: 'error',
      position: 'top',
      duration: 3000,
      isClosable: true,
    });
  }, []);

  return StationPage({
    stations_metadata,
    seoMetadata: seoHomepage,
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
