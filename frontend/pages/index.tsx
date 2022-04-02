import "plyr-react/dist/plyr.css";
import React, {useState} from "react";
import dynamic from "next/dynamic";
import Header from "components/Header/Header";
import Logo from "@/components/Logo/Logo";
import WelcomeMessage from "@/components/WelcomeMessage/WelcomeMessage";
import Container from "@/components/Container/Container";
import StationsGroup from "@/components/StationsGroup/StationsGroup";
import Analytics from "@/components/Analytics/Analytics";
import PageHead from "@/components/PageHead/PageHead";
import {ContactButton} from "@/components/ContactButton/ContactButton";
import {useStations} from "../hooks/stations";
import Body from "@/components/Body/Body";
import Content from "@/components/Content/Content";
import {useLocalStorageState} from "../utils/state";
import {getStationsMetadata} from "../services/stations";
import {Station, StationGroup, StationsMetadata} from "../types";
import StationComponent from "@/components/StationComponent/StationComponent";
import StationHeader from "@/components/StationHeader/StationHeader";

export const StationPlayer = dynamic(() => import("components/RadioPlayer/RadioPlayer"), {
  ssr: true,
});

export default function Home(initialProps: { stationsMetadata: StationsMetadata }) {
  // TODO: Add a message when isLoading/isError are true
  const {stations, station_groups, isLoading, isError} = useStations({
    refreshInterval: 10000,
    initialStationsMetadata: initialProps.stationsMetadata,
  });
  const [selectedStationId, selectStationId] = useLocalStorageState(-1, 'SELECTED_STATION_ID');
  const [started, setStarted] = useState(false);
  const selectedStation = stations.find(s => s.id === selectedStationId);

  const onStationSelect = (station: Station) => {
    console.log("Station selected: ", station, selectedStationId !== station.id);
    setStarted(selectedStationId !== station.id ? true : !started);
    selectStationId(station.id);
  }

  const stationById = stations.reduce(function (previousValue, currentValue) {
    previousValue[currentValue.id] = currentValue;
    return previousValue;
  }, Object.create(null))

  // TODO
  // Align welcome message to the bottom left corner
  // Decrease the height of the header
  // Make the Station title smaller
  // TODO: add an option to search stations (eventually typing directly on the keyboard..)
  return (
    <>
      <PageHead/>

      <Body>
        <Container>
          <StationHeader/>
          {/*<Header>*/}
          {/*  <Logo/>*/}
          {/*  <WelcomeMessage/>*/}
          {/*  <RadioPlayer*/}
          {/*    key={selectedStation?.id}*/}
          {/*    station={selectedStation}*/}
          {/*    started={started}*/}
          {/*    onStop={() => setStarted(false)}*/}
          {/*  />*/}
          {/*</Header>*/}

          {/*<Content>*/}
          {/*  {Object.values(station_groups).sort((a, b) => a.order - b.order).map((g: StationGroup) => {*/}
          {/*    return (*/}
          {/*      <StationsGroup groupName={g.name} key={g.id}>*/}
          {/*        {g.station_to_station_groups.map(s_g => stationById[s_g.station_id]).sort((a, b) => a.order - b.order).map((s) => {*/}
          {/*          return (*/}
          {/*            <StationComponent*/}
          {/*              key={g.id + s.id}*/}
          {/*              station={s}*/}
          {/*              onSelect={onStationSelect}/>*/}
          {/*          );*/}
          {/*        })}*/}
          {/*      </StationsGroup>*/}
          {/*    )*/}
          {/*  })}*/}
          {/*</Content>*/}
        </Container>

        {/*<ContactButton/>*/}
      </Body>

      <Analytics/>
    </>
  );
}


export async function getServerSideProps() {
  const stationsMetadata = await getStationsMetadata();
  return {
    props: {
      stationsMetadata,
    },
    // revalidate: 30,
  };
}
