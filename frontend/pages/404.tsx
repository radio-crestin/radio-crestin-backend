import {useRouter} from 'next/router';
import {Box, Container, useToast} from '@chakra-ui/react';
import {getStationsMetadata} from '../backendServices/stations';
import {StationGroup, StationsMetadata} from '../types';
import {useStations} from '../hooks/stations';
import Body from '@/components/Body/Body';
import Footer from '@/components/Footer/Footer';
import React, {useEffect} from 'react';
import StationList from '@/components/StationList/StationList';
import {ContactModalLink} from '@/components/ContactModalLink/ContactModalLink';
import {SearchStationsModal} from '@/components/SearchStationsModal/SearchStationsModal';

const groupBy = function (xs: any[], key: string) {
  return xs.reduce(function (rv, x) {
    rv[x[key]] = x;
    return rv;
  }, {});
};

export default function NotFoundPage({
  stations_metadata,
}: {
  stations_metadata: StationsMetadata;
}) {
  const router = useRouter();
  const toast = useToast();

  useEffect(() => {
    toast({
      title: `Statia ${router.asPath} nu exista !`,
      status: 'error',
      position: 'bottom-right',
      duration: 10000,
      isClosable: true,
    });
  }, []);

  const {stations, station_groups, isLoading, isError} = useStations({
    refreshInterval: 10000,
    initialStationsMetadata: stations_metadata,
  });

  const stationById = groupBy(stations, 'id');

  // @ts-ignore
  const selectedStationGroup: StationGroup = station_groups.find(
    s => s.slug === 'radio',
  );

  const displayedStations =
    selectedStationGroup?.station_to_station_groups?.map(item => {
      return stationById[item.station_id];
    }) || [];

  return (
    <Body>
      <Container maxW={'8xl'}>
        <Box
          display={'flex'}
          alignItems={'center'}
          justifyContent={'flex-end'}
          gap={5}
          my={5}>
          <ContactModalLink />
          <SearchStationsModal
            station_group={selectedStationGroup}
            stations={stations}
          />
        </Box>
        <StationList
          station_group={selectedStationGroup}
          stations={displayedStations}
        />
        <Footer />
        <Box mb={{base: 40, lg: 20}} />
      </Container>
    </Body>
  );
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
