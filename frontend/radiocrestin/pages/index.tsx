import Head from 'next/head'
import styles from '../styles/Home.module.scss'
import Plyr from 'plyr-react'
import 'plyr-react/dist/plyr.css'
import React, {useEffect, useRef, useState} from "react";
import PlyrJS from "plyr";
import Moment from "react-moment";
import 'moment/locale/ro';
import {addBasePath} from "next/dist/next-server/lib/router/router";

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
  const playingStation = props.station;

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
      // props.onStationStopped();
    });
    player.on('loadeddata', function() {
      // player.elements.display.currentStation.textContent = player.config.title;
    });
    player.on('waiting', function() {
      // player.elements.display.currentStation.textContent = 'Se incarca..';
    });
    player.on('stalled', function() {
      // alert('A aparut o problema neasteptata. Va rugam incercati mai tarziu!')
      player.pause();
      console.trace('stalled', event)
      if (playingStation && remaining_retries > 0) {
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
      src: playingStation?.stream_url,
      type: 'audio/mp3'
    }]
  };
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

const MemoRadioPlayer = React.memo(RadioPlayer, (prevProps, nextProps) => {
  return JSON.stringify(prevProps.station) === JSON.stringify(nextProps.station);
})

export default function Home(initialProps: any) {
  let syncStationsInterval: any;
  const [playerStations, setPlayerStations] = useState(initialProps.stations);


  const getInitialRecommendedStations = () => {
    return playerStations.map((s: any) => {
      return {
        id: s.id,
        plays: 0,
        score: Math.random()
      }
    })
  }

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
    if(playingStation && playingStation.id === stationId) {
      stopStation();
    } else {
      startStation(stationId);
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
                  return <a className={styles.card}  data-selected={playingStation && recommendedStation.id==playingStation.id} key={index} onClick={event => {
                    event.preventDefault();
                    playStation(recommendedStation.id)}
                  }>
                    <h2>{station.title}</h2>
                    <p>{station.stats.current_song}</p>
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
                 data-selected={playingStation && station.id==playingStation.id}
                 onClick={event => {
                event.preventDefault();
                playStation(station.id)
              }}>
                <h2>{station.title}  <small>{station.stats.current_song}</small></h2>
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
      <a href="https://wa.me/40701087702?text=Buna ziua" target="_blank" className={styles.whatsappLink} style={{
        "bottom": playingStation ? "104px" : "32px"
      }}>
        <div className={styles.whatsappLinkBtn}>
          <svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 24 24">
            <path fill="#fff" d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l-.999 3.648 3.742-.981zm11.387-5.464c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.501-.669-.51l-.57-.01c-.198 0-.52.074-.792.372s-1.04 1.016-1.04 2.479 1.065 2.876 1.213 3.074c.149.198 2.095 3.2 5.076 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.695.248-1.29.173-1.414z"/>
          </svg>
        </div>
      </a>

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
