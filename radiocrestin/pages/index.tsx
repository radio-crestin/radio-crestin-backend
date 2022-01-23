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
import {getStaticStationsData} from "./api/v1/stations";
import {StationData} from "../types";
import {useStations} from "../hooks/stations";
import Body from "@/components/Body/Body";
import Station from "@/components/Station/Station";
import Content from "@/components/Content/Content";
import {useLocalStorageState} from "../utils/state";

export const RadioPlayer = dynamic(() => import("components/RadioPlayer/RadioPlayer"), {
  ssr: true,
});

export default function Home(initialProps: { stationsData: StationData[] }) {
  // TODO: Add a message when isLoading/isError are true
  const {stationsData, stationGroups, isLoading, isError} = useStations({
    refreshInterval: 2000,
    initialStationsData: initialProps.stationsData,
  });
  const [selectedStationId, selectStationId] = useLocalStorageState(-1, 'SELECTED_STATION_ID');
  const [started, setStarted] = useState(false);
  const selectedStation = stationsData.find(s => s.id === selectedStationId);

  const onStationSelect = (station: StationData) => {
    console.log("Station selected: ", station, selectedStationId !== station.id);
    setStarted(selectedStationId !== station.id ? true : !started);
    selectStationId(station.id);
  }

  // TODO
  // Align welcome message to the bottom left corner
  // Decrease the height of the header
  // Make the Station title smaller
  //
  return (
    <>
      <PageHead/>

      <Body>
        <Container>
          <Header>
            <Logo/>
            <WelcomeMessage/>
            <RadioPlayer
              station={selectedStation}
              started={started}
              onStop={() => setStarted(false)}
            />
          </Header>

          <Content>
            {Object.values(stationGroups).map((g: any) => {
              return (
                <StationsGroup groupName={g.groupName} key={g.groupName}>
                  {g.stationsData.map((s: any) => (
                    <Station station={s} key={g.groupName + s.title}
                             onSelect={onStationSelect}/>
                  ))}
                </StationsGroup>
              )
            })}
          </Content>
        </Container>

        <ContactButton/>
      </Body>

      <Analytics/>
    </>
  );
}


export async function getStaticProps() {
  return {
    props: {
      stationsData: getStaticStationsData(),
    },
    revalidate: 10,
  };
}
