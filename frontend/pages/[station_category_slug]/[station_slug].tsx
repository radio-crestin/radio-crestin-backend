import React from 'react';
import Head from 'next/head';
import {useRouter} from 'next/router';
import {Box, Container} from '@chakra-ui/react';
import Analytics from '@/components/Analytics/Analytics';
import {useStations} from '../../hooks/stations';
import Body from '@/components/Body/Body';
import {getStationsMetadata} from '../../backendServices/stations';
import {Station, StationGroup, StationsMetadata} from '../../types';
import StationHomepageHeader from '@/components/StationHomepageHeader/StationHomepageHeader';
import StationGroups from '@/components/StationGroups/StationGroups';
import StationList from '@/components/StationList/StationList';
import Footer from '@/components/Footer/Footer';
import {SearchStationsModal} from '@/components/SearchStationsModal/SearchStationsModal';
import {ContactModalLink} from '@/components/ContactModalLink/ContactModalLink';
import {groupBy} from '../../utils/groupBy';

export default function StationPage({
  stations_metadata,
  station_category_slug = 'radio',
  station_slug,
}: {
  stations_metadata: StationsMetadata;
  station_category_slug?: string;
  station_slug?: string;
}) {
  const router = useRouter();
  // TODO: Add a message when isLoading/isError are true
  const {stations, station_groups, isLoading, isError} = useStations({
    refreshInterval: 10000,
    initialStationsMetadata: stations_metadata,
  });

  // @ts-ignore
  const selectedStation: Station = stations.find(s => s.slug === station_slug);

  const stationById = groupBy(stations, 'id');

  // @ts-ignore
  const selectedStationGroup: StationGroup = station_groups.find(
    s => s.slug === station_category_slug,
  );

  const displayedStations =
    selectedStationGroup?.station_to_station_groups?.map(item => {
      return stationById[item.station_id];
    }) || [];

  const seo = selectedStation
    ? {
        title: `${selectedStation.title + ' · LIVE  ·'} Radio Crestin `,
        description: `${selectedStation?.title} · 📻 ${
          selectedStation?.description
            ? selectedStation?.description
            : `Asculta ${selectedStation?.title} live · Lista de radiouri crestine · Radio Crestin Live`
        }`,
        keywords: `${selectedStation?.title}, asculta ${selectedStation?.title} live, post radio, live, radio crestin online, cantari, crestine, radiouri, muzica crestina, lista radio crestin, asculta radio crestin online, radio fm crestine, lista radio crestin online, \t
  radio crestin muzica non stop,  radio-crestin.com`,
      }
    : {
        title: `Lista de radiouri crestine`,
        description: `Asculta radio crestin 📻 · Peste 25 de posturi de radio`,
        keywords: `post radio, live, radio crestin online, cantari, crestine, radiouri, muzica crestina, lista radio crestin, asculta radio crestin online, radio fm crestine, lista radio crestin online, \t
  radio crestin muzica non stop, radio-crestin.com`,
      };

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
        </Container>
      </Body>
      <Analytics />
    </>
  );
}

export async function getServerSideProps(context: any) {
  const stations_metadata = await getStationsMetadata();

  const {station_category_slug, station_slug} = context.query;
  return {
    props: {
      stations_metadata,
      station_category_slug,
      station_slug,
    },
  };
}
