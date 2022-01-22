import "plyr-react/dist/plyr.css";
import React from "react";
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

export const RadioPlayer = dynamic(() => import("components/RadioPlayer/RadioPlayer"), {
  ssr: true,
});

export default function Home(initialProps: { stationsData: StationData[] }) {
  const {stationsData, isLoading, isError} = useStations({
    refreshInterval: 2000,
    initialStationsData: initialProps.stationsData,
  });
  // TODO: Add a message when isLoading/isError

  // TODO: extract group name from stationsData
  const stationGroups = {
    general: {
      groupName: "General",
      stationsData: stationsData,
    },
    muzica: {
      groupName: "Muzica",
      stationsData: stationsData,
    },
  };

  const onStationSelect = (station: StationData) => {
    console.log("Station selected: ", station);
  }

  return (
    <>
      <PageHead/>

      <Body>
        <Container>
          <Header>
            <Logo/>
            <WelcomeMessage/>
            <RadioPlayer/>
          </Header>

          <Content>
            {Object.values(stationGroups).map((g: any) => {
              return (
                <StationsGroup groupName={g.groupName} key={g.groupName}>
                  {g.stationsData.map((s: any) => (
                    <Station stationData={s} key={g.groupName + s.title}
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
