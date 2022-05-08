import React from "react";
import Analytics from "@/components/Analytics/Analytics";
import { useStations } from "../hooks/stations";
import Body from "@/components/Body/Body";
import { useLocalStorageState } from "../utils/state";
import { getStationsMetadata } from "../backendServices/stations";
import { Station, StationsMetadata } from "../types";
import StationHomepageHeader from "@/components/StationHeader/StationHeader";
import StationGroups from "@/components/StationGroups/StationGroups";
import StationList from "@/components/StationList/StationList";
import {Box, Container} from "@chakra-ui/react";
import HeaderMenu from "@/components/HeaderMenu/HeaderMenu";

const groupBy = function(xs: any[], key: string) {
  return xs.reduce(function(rv, x) {
    rv[x[key]] = x;
    return rv;
  }, {});
};

export default function Home(initialProps: {
  stationsMetadata: StationsMetadata;
}) {
  // TODO: Add a message when isLoading/isError are true
  const { stations, station_groups, isLoading, isError } = useStations({
    refreshInterval: 10000,
    initialStationsMetadata: initialProps.stationsMetadata,
  });

  const random = (a: any[]) => a.find((_, i, ar) => Math.random() < 1 / (ar.length - i))

  const [selectedStationId, selectStationId] = useLocalStorageState(
    random(stations).id,
    "SELECTED_STATION_ID",
  );

  const [selectedStationGroupId, selectStationGroupId] = useLocalStorageState(
    station_groups[0].id,
    "SELECTED_STATION_GROUP_ID",
  );

  const selectedStation = stations.find(s => s.id === selectedStationId);

  const stationById = groupBy(stations, 'id');

  const displayedStations = station_groups.find(s => s.id === selectedStationGroupId)?.station_to_station_groups?.map((item) => {
     return stationById[item.station_id];
  }) || [];

  const pickARandomStation = () => {
    selectStationId(random(stations).id)
  }

  // TODO
  // Align welcome message to the bottom left corner
  // Decrease the height of the header
  // Make the Station title smaller
  // TODO: add an option to search stations (eventually typing directly on the keyboard..)

  // console.log(stations);

  return (
    <>
      <Body>
        <Container maxW={'8xl'}>
          <HeaderMenu />
          {selectedStation && <StationHomepageHeader selectedStation={selectedStation} pickARandomStation={pickARandomStation} />}
          <StationGroups stationGroups={station_groups} selectedStationGroupId={selectedStationGroupId} selectStationGroupId={selectStationGroupId}/>
          <StationList stations={displayedStations} onStationSelect={(station: Station) => {
            selectStationId(station.id);
          }} />
          <Box mb={{base: 40, lg: 20}}/>
        </Container>
      </Body>
      <Analytics />
    </>
  );
}

export async function getServerSideProps() {
  const stationsMetadata = await getStationsMetadata();
  return {
    props: {
      stationsMetadata,
    },
  };
}
