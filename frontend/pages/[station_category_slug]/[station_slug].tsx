import React, {useEffect, useState} from 'react';
import Head from 'next/head';
import {Box, Container, useToast} from '@chakra-ui/react';
import dynamic from 'next/dynamic';

import Analytics from '@/components/Analytics/Analytics';
import Body from '@/components/Body/Body';
import {getStationsMetadata} from '../../backendServices/stations';
import {
  SeoMetadata,
  Station,
  StationGroup,
  StationsMetadata,
} from '../../types';
import StationHomepageHeader from '@/components/StationHomepageHeader/StationHomepageHeader';
import StationGroups from '@/components/StationGroups/StationGroups';
import StationList from '@/components/StationList/StationList';
import Footer from '@/components/Footer/Footer';
import {SearchStationsModal} from '@/components/SearchStationsModal/SearchStationsModal';
import {ContactModalLink} from '@/components/ContactModalLink/ContactModalLink';
import {indexBy} from '@/utils/indexBy';
import {seoStation} from '@/utils/seo';

const StationPlayer = dynamic(() => import('@/components/StationPlayer'), {
  ssr: false,
});

export default function StationPage({
  stations_metadata,
  station_category_slug = 'radio',
  station_slug,
  seoMetadata,
}: {
  stations_metadata: StationsMetadata;
  station_category_slug?: string;
  station_slug?: string;
  seoMetadata?: SeoMetadata;
}) {
  const toast = useToast();
  const [stations, setStations] = useState(stations_metadata.stations);
  const [station_groups, setStation_groups] = useState(
    stations_metadata.station_groups,
  );

  useEffect(() => {
    const fetchStations = setInterval(() => {
      fetch('/api/v1/stations').then(async r => {
        const data = await r.json();
        if (!data) {
          toast({
            title: 'A apărut o eroare neașteptată.',
            description:
              'În cazul în care eroarea persistă, va rugăm să ne trimiteți un mesaj pe whatsapp: +4 0773 994 595. Va mulțumim!',
            status: 'error',
            position: 'top',
            duration: 14000,
            isClosable: true,
          });
          return;
        }
        setStations(data.stations);
        setStation_groups(data.station_groups);
      });
    }, 10000);
    return () => clearInterval(fetchStations);
  }, []);

  // @ts-ignore
  const selectedStation: Station = stations.find(s => s.slug === station_slug);

  const stationById = indexBy(stations, 'id');

  // @ts-ignore
  const selectedStationGroup: StationGroup = station_groups.find(
    s => s.slug === station_category_slug,
  );

  const displayedStations =
    selectedStationGroup?.station_to_station_groups?.map(item => {
      return stationById[item.station_id];
    }) || [];

  const seo: SeoMetadata =
    seoMetadata ||
    seoStation(selectedStation.title, selectedStation.description);

  return (
    <>
      <Head>
        <title>{seo.title}</title>
        <meta property="title" content={seo?.title} />
        <meta name="description" content={seo?.description} />
        <meta property="og:title" content={seo?.title} />
        <meta name="og:description" content={seo?.description} />
        <meta property="og:site_name" content="Radio Crestin" />
        <meta property="og:type" content="article" />
        <meta name="twitter:title" content={seo?.title} />
        <meta name="twitter:description" content={seo?.description} />
        <meta name="twitter:title" content={seo?.title} />
        <meta name="twitter:card" content="summary" />
        <meta name="keywords" content={seo?.keywords} />
        <meta name="viewport" content="initial-scale=1.0, width=device-width" />
      </Head>
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
          {selectedStation && (
            <StationHomepageHeader selectedStation={selectedStation} />
          )}
          <StationGroups
            stationGroups={station_groups}
            selectedStation={selectedStation}
            selectedStationGroup={selectedStationGroup}
          />
          <StationList
            station_group={selectedStationGroup}
            stations={displayedStations}
          />
          <Footer />
          <Box mb={{base: 40, lg: 20}} />
          <StationPlayer stations={stations} />
        </Container>
      </Body>
      <Analytics />
    </>
  );
}

export async function getServerSideProps(context: any) {
  context.res.setHeader(
    'Cache-Control',
    'public, s-maxage=10, stale-while-revalidate=59',
  );
  const stations_metadata = await getStationsMetadata();
  const {station_category_slug, station_slug} = context.query;

  const stationData = stations_metadata.stations.find(
    station => station.slug === station_slug,
  );

  if (!stationData) {
    return {
      redirect: {
        permanent: false,
        destination: `/?error=Statia ${station_slug} nu a fost gasita`,
      },
    };
  }

  return {
    props: {
      stations_metadata,
      station_category_slug,
      station_slug,
    },
  };
}
