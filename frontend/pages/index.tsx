import "plyr-react/dist/plyr.css";
import React, { useState } from "react";
import dynamic from "next/dynamic";
import Container from "@/components/Container/Container";
import Analytics from "@/components/Analytics/Analytics";
import PageHead from "@/components/PageHead/PageHead";
import { useStations } from "../hooks/stations";
import Body from "@/components/Body/Body";
import { useLocalStorageState } from "../utils/state";
import { getStationsMetadata } from "../services/stations";
import { Station, StationGroup, StationsMetadata } from "../types";
import StationHeader from "@/components/StationHeader/StationHeader";
import StationCategories from "@/components/StationCategories/StationCategories";
import Stations from "@/components/Stations/Stations";
import Footer from "@/components/Footer/Footer";

export default function Home(initialProps: {
  stationsMetadata: StationsMetadata;
}) {
  // TODO: Add a message when isLoading/isError are true
  const { stations, station_groups, isLoading, isError } = useStations({
    refreshInterval: 10000,
    initialStationsMetadata: initialProps.stationsMetadata,
  });

  const [selectedStationId, selectStationId] = useLocalStorageState(
    -1,
    "SELECTED_STATION_ID",
  );
  const [started, setStarted] = useState(false);
  const selectedStation = stations.find(s => s.id === selectedStationId);

  const onStationSelect = (station: Station) => {
    console.log(
      "Station selected: ",
      station,
      selectedStationId !== station.id,
    );
    setStarted(selectedStationId !== station.id ? true : !started);
    selectStationId(station.id);
  };

  const stationById = stations.reduce(function (previousValue, currentValue) {
    previousValue[currentValue.id] = currentValue;
    return previousValue;
  }, Object.create(null));

  // TODO
  // Align welcome message to the bottom left corner
  // Decrease the height of the header
  // Make the Station title smaller
  // TODO: add an option to search stations (eventually typing directly on the keyboard..)

  // console.log(stations);

  return (
    <>
      <PageHead />

      <Body>
        <Container>
          {selectedStation && <StationHeader {...selectedStation} />}
          <StationCategories />
          <Stations stations={stations} onStationSelect={onStationSelect} />
          <Footer />
        </Container>
      </Body>
      <Analytics />
    </>
  );
}

export async function getServerSideProps() {
  const stationsMetadata = await getStationsMetadata({ serverSide: true });
  return {
    props: {
      stationsMetadata,
    },
  };
}
