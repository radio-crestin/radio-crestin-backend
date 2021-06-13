import Head from 'next/head'
import styles from '../styles/Home.module.scss'
import Plyr from 'plyr-react'
import 'plyr-react/dist/plyr.css'
import React, {useEffect, useRef, useState} from "react";
import PlyrJS from "plyr";
import Moment from "react-moment";
import 'moment/locale/ro';

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


export function RadioPlayer(props: any) {
  const playingStation = React.useMemo(
      () => props.station,
      props.station
  );

  let remaining_retries = 5;
  let remaining_error_retries = 5;

  const playerRef = useRef()
  useEffect(() => {
    // @ts-ignore
    const player = playerRef.current.plyr;

    if(typeof player.config.title === "undefined") {
      // @ts-ignore
      player.stop();

    } else {
      // @ts-ignore
      player.play();
    }
    player.on('pause', function() {
      props.onStationStopped();
    });
    player.on('loadeddata', function() {
      // player.elements.display.currentStation.textContent = player.config.title;
    });
    player.on('waiting', function() {
      // player.elements.display.currentStation.textContent = 'Se incarca..';
    });
    player.on('stalled', function() {
      alert('A aparut o problema neasteptata. Va rugam incercati mai tarziu!')
      player.pause();
      console.trace('stalled', event)
      if (!player.media.paused && remaining_retries > 0) {
        setTimeout(function() {
          console.log("Retrying to play..")
          // player.source = lastPlayerSource;
          player.play();
          remaining_retries--;
        }, remaining_retries === 5 ? 0 : 1000);
      }
    });
    player.on('error', function(event: any) {
      console.trace('error', event)
      if (!player.media.paused && event.detail.plyr.media.error && event.detail.plyr.failed && remaining_error_retries > 0) {
        setTimeout(function() {
          console.log("Retrying to play..")
          // player.source = lastPlayerSource;
          player.play();
          remaining_error_retries--;
        }, remaining_error_retries === 5 ? 0 : 1000);
      }

    });
  })
  const playerSrc: PlyrJS.SourceInfo = {
    type: 'audio',
    title: playingStation?.title,
    sources: [{
      src: playingStation?.url,
      type: 'audio/mp3'
    }]
  };

  console.log("rendering radio")
  return <Plyr
      ref={playerRef}
      source={playerSrc}
      options={
        {
          debug: false,
          settings: ['quality'],
          autoplay: false,
          volume: 0.8,
          resetOnEnd: true,
          invertTime: false,
          controls: ['play', 'current-station1', 'current-time', 'mute', 'volume', 'pip', 'airplay'],
        }
      }/>
}

export default function Home(initialProps: any) {
  let syncStationsInterval: any;
  const [playerStations, setPlayerStations] = useState(initialProps.stations);
  const [recentPlayedStations, setRecentPlayedStations] = useStickyState([], 'RECENT_PLAYED_STATIONS');
  const [playingStationId, originalSetPlayingStationId] = useState(-1);
  const [t, setTest] = useState(-1);

  useEffect(() => {
    console.trace("starting interval")
    if(typeof syncStationsInterval === "undefined") {
      syncStationsInterval = setInterval(async () => {
        setTest(2)
        console.log("refresh stations")
      }, 2000);
    }
    // return () => {
    //   clearInterval(syncStationsInterval);
    // }
  });
  const setPlayingStationId = (stationId: number) => {
    originalSetPlayingStationId(stationId);
    if(stationId !== -1) {
      let newRecentPlayedStationsIds = JSON.parse(JSON.stringify(recentPlayedStations));
      newRecentPlayedStationsIds.push({
        id: stationId,
        timestamp: (new Date()).toISOString(),
      });
      newRecentPlayedStationsIds = newRecentPlayedStationsIds.filter((value: any, index: any, self: any) => {
        return self.indexOf(self.find((v: any) => v.id === value.id)) === index;
      });
      newRecentPlayedStationsIds = newRecentPlayedStationsIds.sort((n1: any,n2: any) => n2.timestamp - n1.timestamp);
      newRecentPlayedStationsIds = newRecentPlayedStationsIds.slice(0, 4);
      setRecentPlayedStations(newRecentPlayedStationsIds);
    }
  }


  const playStation = (stationId: number) => {
    if(playingStationId === stationId) {
      setPlayingStationId(-1);
    } else {
      setPlayingStationId(stationId);
    }
  }

  return (
    <div className={styles.container}>
      <Head>
        <title>Radio Crestin</title>
        <meta name="description" content="Lista de radiouri crestine." />
        <link rel="icon" href="/favicon.ico" />
        <style>
        {
          `#radio_player {
            opacity: ${playingStationId !== -1 ? "1": "0"}
          }
        `}
      </style>
      </Head>

      <main className={styles.main}>
        <h1 className={styles.title}>
          Radiouri <span className={styles.highlighted_title}>Creștine</span>
        </h1>

        <div className={styles.grid} style={{marginTop: "4rem"}}>
          <h2 className={styles.section_subtitle}>Recomandate pentru tine</h2>
          {recentPlayedStations.map((recentPlayedStation: any, index: number) => {
            const station = playerStations?.find(o => o.id === recentPlayedStation.id);
            if(station) {
              return <a className={styles.card}  data-selected={recentPlayedStation.id==playingStationId} key={index} onClick={event => {
                event.preventDefault();
                playStation(recentPlayedStation.id)}
              }>
                <h2>{station.title}</h2>
                <p>{station.current_song}</p>
                {recentPlayedStation.timestamp ? <Moment fromNow>{new Date(recentPlayedStation.timestamp)}</Moment> : null}
              </a>
            } else {
              return null;
            }
          }
              )}
        </div>


        <div className={styles.grid}>
          <h2 className={styles.section_subtitle}>Stații de radiouri creștine</h2>
          {/*<input  className={styles.search_card} type="text" placeholder="Tasteaza numele statiei.." name="search"/>*/}
          {playerStations?.map((station: any, index: number) =>
              <a className={styles.radio_station_link} key={index} onClick={event => {
                event.preventDefault();
                playStation(station.id)
              }}>
              <h2>{station.title}</h2>
            </a>)}
        </div>
        <div className={styles.radio_player_wrapper}>
          <div id="radio_player" className={styles.radio_player}>
            <RadioPlayer
            station={playerStations[0]}
            onStationStopped={() => setPlayingStationId(-1)}
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
    </div>
  )

}
Home.getInitialProps = async (ctx: any) => {
  return { stations: await getStations() }
}

async function getStations() {
  const res = await fetch('https://api.radio-crestin.ro/stations')
  return (await res.json())["stations"]
}
