import React, {useEffect} from 'react';
import {useRouter} from 'next/router';
import {useToast} from '@chakra-ui/react';
import {getStationsMetadata} from '../backendServices/stations';
import {StationsMetadata} from '../types';

export default function Home({
  stations_metadata,
}: {
  stations_metadata: StationsMetadata;
  message: string;
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

  return <>123</>;
}

export async function getServerSideProps(context: any) {
  context.res.setHeader(
    'Cache-Control',
    'public, s-maxage=10, stale-while-revalidate=59',
  );
  const stations_metadata = await getStationsMetadata();
  return {
    props: {
      stations_metadata,
    },
  };
}
