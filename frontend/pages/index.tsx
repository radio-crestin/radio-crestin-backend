import React, {useEffect} from 'react';
import {useRouter} from 'next/router';
import {useToast} from '@chakra-ui/react';
import {getStationsMetadata} from '../backendServices/stations';
import {StationsMetadata} from '../types';
import StationPage from './[station_category_slug]/[station_slug]';
import {seoHomepage} from '@/utils/seo';

export default function Home({
  stations_metadata,
  fullURL,
}: {
  stations_metadata: StationsMetadata;
  message: string;
  fullURL: string;
}) {
  const router = useRouter();
  const toast = useToast();

  useEffect(() => {
    if (router.query.error) {
      toast({
        title: `Eroare!`,
        description: <p>{router.query.error}</p>,
        status: 'error',
        position: 'top',
        duration: 4000,
        isClosable: true,
      });
    }
  }, []);

  return StationPage({
    stations_metadata,
    seoMetadata: seoHomepage,
    fullURL: fullURL,
  });
}

export async function getServerSideProps(context: any) {
  const {req, res} = context;
  res.setHeader(
    'Cache-Control',
    'public, s-maxage=10, stale-while-revalidate=59',
  );
  const host = req.headers.host;
  const stations_metadata = await getStationsMetadata();
  return {
    props: {
      stations_metadata,
      fullURL: `https://www.${host}`,
    },
  };
}
