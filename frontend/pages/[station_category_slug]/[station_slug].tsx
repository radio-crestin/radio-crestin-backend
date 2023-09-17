import React, {useEffect, useState} from 'react';
import {Box, Container} from '@chakra-ui/react';
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
import {parse} from 'url';
import HeadContainer from '@/components/HeadContainer';
import DownloadAppBanner from '@/components/DownloadAppBanner/DownloadAppBanner';

const StationPlayer = dynamic(() => import('@/components/StationPlayer'), {
  ssr: false,
});

export default function StationPage({
                                      stations_metadata,
                                      station_category_slug = 'radio',
                                      station_slug,
                                      seoMetadata,
                                      fullURL,
                                    }: {
  stations_metadata: StationsMetadata;
  station_category_slug?: string;
  station_slug?: string;
  seoMetadata?: SeoMetadata;
  fullURL: string;
}) {
  const [stations, setStations] = useState(stations_metadata.stations);
  const [station_groups, setStation_groups] = useState(
    stations_metadata.station_groups,
  );

  useEffect(() => {
    const fetchStations = setInterval(() => {
      fetch('/api/v1/stations').then(async r => {
        const data = await r.json();
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
    seoStation(selectedStation?.title, selectedStation.description);

  return (
    <>
      <HeadContainer
        seo={seo}
        fullURL={fullURL}
        selectedStation={selectedStation}
      />
      <Body>
        <Container maxW={'8xl'}>
          <Box
            display={'flex'}
            alignItems={'center'}
            justifyContent={'flex-end'}
            my={4}
            gap={2}>
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
          <DownloadAppBanner />
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
  const {req, res, query} = context;
  res.setHeader(
    'Cache-Control',
    'public, s-maxage=10, stale-while-revalidate=59',
  );
  const stations_metadata = await getStationsMetadata();
  const {station_category_slug, station_slug} = query;
  const stationData = stations_metadata.stations.find(
    station => station.slug === station_slug,
  );
  const {pathname} = parse(req.url, true);
  const host = req.headers.host;

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
      fullURL: `https://www.${host}${pathname}`,
    },
  };
}
