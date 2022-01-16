import Head from 'next/head'
import 'plyr-react/dist/plyr.css'
import React, {useEffect, useState} from "react";
import dynamic from 'next/dynamic';
import {isMobile} from 'react-device-detect';
import useSWR from 'swr'
import {getStations} from "./api/v1/stations";
import Header from "components/Header/Header";

const fetcher = (url: string) => fetch(url).then((res) => res.json())

function useStickyState(defaultValue: any, key: any) {
  const [value, setValue] = useState(() => {
    const stickyValue = typeof window !== "undefined" ? window.localStorage.getItem(key) : null;
    return stickyValue !== null
        ? JSON.parse(stickyValue)
        : defaultValue;
  });
  useEffect(() => {
    const stickyValue = typeof window !== "undefined" ? window.localStorage.getItem(key) : null;
    if(stickyValue !== null) {
      setValue(JSON.parse(stickyValue));
    }
  }, [key, setValue]);

  useEffect(() => {
    window.localStorage.setItem(key, JSON.stringify(value));
  }, [key, value]);
  return [value, setValue];
}

const ContactButton = dynamic(() => isMobile ? import("components/WhatsAppButton") : import("components/EmailButton"), { ssr: false })

const RadioPlayer = dynamic(() => import("components/RadioPlayer/RadioPlayer"), { ssr: true })

const MemoRadioPlayer = React.memo(RadioPlayer, (prevProps, nextProps) => {
  return JSON.stringify(prevProps.station) === JSON.stringify(nextProps.station);
})

export default function Home(initialProps: any) {
  const [recommendedStations, setRecommendedStations] = useStickyState({}, 'RECOMMENDED_STATIONS');
  const [playingStation, originalSetPlayingStation] = useState();
  const [searchValue, setSearchValue] = useState("");


  const { data, error } = useSWR('/api/v1/stations', fetcher, {
    refreshInterval: 2000
  });
  if(error) {
    console.error(error);
  }
  if (error) {
    console.error("An error has occurred. Please retry later!");
  }
  let playerStations: any[];
  if (!data) {
    playerStations = initialProps.stations;
  } else {
    playerStations = data["stations"];
  }
  useEffect(() => {
    playerStations.forEach((station: any) => {
      let changed = false;
      if(!recommendedStations[station.id]) {
        recommendedStations[station.id] = {
          id: station.id,
          plays: 0,
          score: Math.random(),
        };
        changed = true;
      }
      if(changed) {
        return setRecommendedStations(recommendedStations);
      }
    })
  }, [playerStations]);


  const startStation = (stationId: number) => {
    originalSetPlayingStation(JSON.parse(JSON.stringify(playerStations.find((s:any) => s.id === stationId))));
    let newRecommendedStations = JSON.parse(JSON.stringify(recommendedStations));
    let stationRecommendation = newRecommendedStations[stationId] || {
      id: stationId,
      plays: 0,
    };
    stationRecommendation.plays++;
    newRecommendedStations[stationId] = stationRecommendation;

    // Recalculate the score
    const totalPlays = Object.values(newRecommendedStations).reduce((accumulator: number, currentValue: any) => accumulator + currentValue.plays, 0);
      Object.keys(newRecommendedStations).forEach(function(key) {newRecommendedStations[key].score = newRecommendedStations[key].plays/totalPlays;
    });
    setRecommendedStations(newRecommendedStations);
  }

  const stopStation = () => {
    originalSetPlayingStation(undefined);
  }


  const playStation = (stationId: number) => {
    // @ts-ignore
    if(playingStation && playingStation.id === stationId) {
      stopStation();
    } else {
      startStation(stationId);
    }
  }

  // @ts-ignore
  return (
    <div>
      <Head>
        <title>Radio Crestin</title>
        <meta name="description" content="Lista de radiouri crestine." />
        <link rel="icon" href="/favicon.ico" />
        <style>
        {
          `#radio_player {
            opacity: ${playingStation ? "1": "0"}
          }
        `}
      </style>
      </Head>

      <main>
        <Header />
      </main>
      <ContactButton isPlaying={playingStation}/>

      <script defer src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{"token": "c2153a600cc94f69848e4decff1983a1"}'/>
      <script async src="https://www.googletagmanager.com/gtag/js?id=UA-204935415-1">
      </script>
      <script src="/ga.js"></script>
      <script src="/hj.js"></script>
    </div>
  )

}

export async function getStaticProps() {
  const s = (await getStations());

  const stations = s.map((s: any) => {
    s["listeners"] = null;
    return s;
  });
  console.log("stations: ", stations);
  return {
    props: {
      stations
    }
  }
}
