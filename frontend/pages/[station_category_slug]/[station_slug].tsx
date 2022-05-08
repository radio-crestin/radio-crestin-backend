import React, {useEffect} from "react";
import Analytics from "@/components/Analytics/Analytics";
import { useStations } from "../../hooks/stations";
import Body from "@/components/Body/Body";
import { useLocalStorageState } from "../../utils/state";
import { getStationsMetadata } from "../../backendServices/stations";
import {Station, StationGroup, StationsMetadata} from "../../types";
import StationHomepageHeader from "@/components/StationHomepageHeader/StationHomepageHeader";
import StationGroups from "@/components/StationGroups/StationGroups";
import StationList from "@/components/StationList/StationList";
import {Box, Container} from "@chakra-ui/react";
import HeaderMenu from "@/components/HeaderMenu/HeaderMenu";
import {useRouter} from "next/router";

const groupBy = function(xs: any[], key: string) {
  return xs.reduce(function(rv, x) {
    rv[x[key]] = x;
    return rv;
  }, {});
};

export default function StationPage({
                                      stations_metadata,
                                      station_category_slug,
                                      station_slug,
                                    }: {
  stations_metadata: StationsMetadata,
  station_category_slug: string,
  station_slug: string
}) {
  // TODO: Add a message when isLoading/isError are true
  const { stations, station_groups, isLoading, isError } = useStations({
    refreshInterval: 10000,
    initialStationsMetadata: stations_metadata,
  });

  const random = (a: any[]) => a.find((_, i, ar) => Math.random() < 1 / (ar.length - i))

  const [selectedStationSlug, selectStationSlug] = useLocalStorageState(
    random(stations).slug,
    "SELECTED_STATION_SLUG",
  );

  const [selectedStationGroupSlug, selectStationGroupSlug] = useLocalStorageState(
    station_groups[0].slug,
    "SELECTED_STATION_GROUP_SLUG",
  );


  // @ts-ignore
  const selectedStation: Station = stations.find(s => s.slug === station_slug);

  const stationById = groupBy(stations, 'id');

  // @ts-ignore
  const selectedStationGroup: StationGroup = station_groups.find(s => s.slug === station_category_slug);

  const displayedStations = selectedStationGroup?.station_to_station_groups?.map((item) => {
    return stationById[item.station_id];
  }) || [];

  const pickARandomStation = () => {
    selectStationSlug(random(stations).slug)
  }

  useEffect(() => {
    selectStationSlug(station_slug)
    selectStationGroupSlug(station_category_slug)
  }, [])


  // TODO
  // TODO: add an option to search stations (eventually typing directly on the keyboard..)

  return (
    <>
      <Body>
        <Container maxW={'8xl'}>
          <HeaderMenu />
          {selectedStation && <StationHomepageHeader selectedStation={selectedStation} pickARandomStation={pickARandomStation}/> }
          <StationGroups
            stationGroups={station_groups}
            selectedStation={selectedStation}
            selectedStationGroup={selectedStationGroup} />
          <StationList station_group={selectedStationGroup} stations={displayedStations} />
          <Box mb={{base: 40, lg: 20}}/>
        </Container>
      </Body>
      <Analytics />
    </>
  );
}

export async function getServerSideProps(context: any) {
  const stations_metadata = await getStationsMetadata();

  const { station_category_slug, station_slug } = context.query
  return {
    props: {
      stations_metadata,
      station_category_slug,
      station_slug
    },
  };
}
