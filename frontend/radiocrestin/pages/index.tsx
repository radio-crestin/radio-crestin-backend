import Head from 'next/head'
import styles from '../styles/Home.module.scss'
import 'plyr-react/dist/plyr.css'
import React, {useEffect, useState} from "react";
import dynamic from 'next/dynamic';

import {isMobile} from 'react-device-detect';
import Marquee from 'react-fast-marquee'

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

const ContactButton = dynamic(() => isMobile ? import("../components/WhatsAppButton") : import("../components/EmailButton"), { ssr: false })

const RadioPlayer = dynamic(() => import("../components/RadioPlayer"), { ssr: true })

const MemoRadioPlayer = React.memo(RadioPlayer, (prevProps, nextProps) => {
  return JSON.stringify(prevProps.station) === JSON.stringify(nextProps.station);
})

export default function Home(initialProps: any) {
  let syncStationsInterval: any;
  const [playerStations, setPlayerStations] = useState(initialProps.stations);
  const [recommendedStations, setRecommendedStations] = useStickyState({}, 'RECOMMENDED_STATIONS');
  const [playingStation, originalSetPlayingStation] = useState();
  const [searchValue, setSearchValue] = useState("");

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

  useEffect(() => {
    if(typeof syncStationsInterval === "undefined") {
      syncStationsInterval = setInterval(() => {
        getStations().then(stations => setPlayerStations(stations));
      }, 30000);
      getStations().then(stations => setPlayerStations(stations));
    }
    return () => {
      clearInterval(syncStationsInterval);
    }
  }, []);


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
    <div className={styles.container}>
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

      <main className={styles.main}>
        <h1 className={styles.title}>
          Radiouri <span className={styles.highlighted_title}>Creștine</span>
        </h1>

        <div className={styles.grid} style={{marginTop: "4rem"}}>
          <div className={styles.recommended_stations}>
            <h2 className={styles.section_subtitle}>Recomandate pentru tine</h2>
            {Object.values(recommendedStations).sort((a: any, b: any) => {
              return b.score - a.score;
            }).slice(0, 4).map((recommendedStation: any, index: number) => {
                  const station = playerStations?.find((o: any) => o.id === recommendedStation.id);
                  // @ts-ignore
                  return <a className={styles.card}  data-selected={playingStation && recommendedStation.id==playingStation.id} key={index} onClick={event => {
                    event.preventDefault();
                    playStation(recommendedStation.id)}
                  }>
                    <h2>{station.title}</h2>

                    <p><Marquee speed={10} delay={10} gradient={false} play={station.stats.current_song.length > 30}>{station.stats.current_song}</Marquee></p>
                    <small>{station.stats.listeners > 0? `${station.stats.listeners} ascultători` : ""}</small>
                  </a>
                }
            )}
          </div>
        </div>


        <div className={styles.grid}>
          <h2 className={styles.section_subtitle}>Stații de radiouri creștine</h2>

          <input
              className={styles.search_card}
              type="text"
              placeholder="Tastează numele stației.."
              name="search"
              value={searchValue}
              onChange={e=> setSearchValue(e.target.value.trim())}
          />

          {playerStations?.filter((station: any) => {
            return searchValue === "" || station.title.toLowerCase().includes(searchValue.toLowerCase())
          })?.map((station: any, index: number) =>
              <a className={styles.radio_station_link}
                 key={index}
                  // @ts-ignore
                 data-selected={playingStation && station.id==playingStation.id}
                 onClick={event => {
                event.preventDefault();
                playStation(station.id)
              }}>
                <h2>{station.title}  <small><Marquee speed={10} delay={10} gradient={false} play={station.stats.current_song.length > 30}>{station.stats.current_song}</Marquee></small></h2>
            </a>)}
        </div>
        <div className={styles.radio_player_wrapper}>
          <div id="radio_player" className={styles.radio_player}>
            <MemoRadioPlayer
            station={playingStation}
            onStationStopped={stopStation}
            />
          </div>
        </div>
      </main>

      {/*<footer className={styles.footer}>*/}
      {/*  /!*<a*!/*/}
      {/*  /!*  href="https://vercel.com?utm_source=create-next-app&utm_medium=default-template&utm_campaign=create-next-app"*!/*/}
      {/*  /!*  target="_blank"*!/*/}
      {/*  /!*  rel="noopener noreferrer"*!/*/}
      {/*  /!*>*!/*/}
      {/*  /!*  Powered by{' '}*!/*/}
      {/*  /!*  <span className={styles.logo}>*!/*/}
      {/*  /!*    <Image src="/vercel.svg" alt="Vercel Logo" width={72} height={16} />*!/*/}
      {/*  /!*  </span>*!/*/}
      {/*  /!*</a>*!/*/}
      {/*</footer>*/}
      <ContactButton isPlaying={playingStation}/>

      <script defer src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{"token": "b46514f4157046a2b57c4b1872c09ef9"}'/>
    </div>
  )

}
Home.getInitialProps = async (ctx: any) => {
  return { stations: (await getStations()).map((s: any) => {
    s["listeners"] = null;
    return s;
    }) }
}

async function getStations() {
  const res = await fetch(`https://api.radio-crestin.ro/stations`)
  return (await res.json())["stations"]
}
