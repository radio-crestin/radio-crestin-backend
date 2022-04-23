import React, {useMemo, useState} from "react";
import styles from "./StationPlayer.module.scss";
import { Station } from "../../types";
import {CONSTANTS} from "../../lib/constants";
import ReactPlayer from "react-player";
import InputRange from "react-input-range";

import 'react-input-range/lib/css/index.css'
import {useLocalStorageState} from "../../utils/state";

let firstStart = true;
const STREAM_TYPE_INFO: any = {
  "HLS":  {
      field: "hls_stream_url",
      name: "hls"
    },
  "PROXY": {
      field: "proxy_stream_url",
      name: "proxy"
    },
  "ORIGINAL": {
      field: "stream_url",
      name: "original"
    },
}
const MAX_MEDIA_RETRIES = 20;

export default function StationPlayer(props: {
  station?: Station;
}) {
  const { station } = props;

  console.debug("station:", station)

  if (typeof station === "undefined") {
    return <></>;
  }

  const [retries, setRetries] = useState(MAX_MEDIA_RETRIES);

  const [playing, setPlaying] = useState(!firstStart);
  firstStart = false;

  // TODO: we might need to populate these from local storage
  const [volume, setVolume] = useLocalStorageState(60, "AUDIO_PLAYER_VOLUME");

  const [selectedStreamType, setSelectedStreamType] = useState(
    "HLS",
  );

  const retryMechanism = async () => {
    console.debug("retryMechanism called")
    console.debug("waiting 1s")
    await new Promise(r => setTimeout(r, 1000));
    setRetries(retries - 1);
    console.debug("remaining retries: ", retries);
    if(retries > 0) {
      if(selectedStreamType === "HLS") {
        setSelectedStreamType("PROXY")
        return true;
      }
      if(selectedStreamType === "PROXY") {
        setSelectedStreamType("ORIGINAL")
        return true;
      }
      if(selectedStreamType === "ORIGINAL") {
        setSelectedStreamType("HLS")
        return true;
      }
    }
    return false;
  }

  // @ts-ignore
  const station_url = station[STREAM_TYPE_INFO[selectedStreamType as string].field];

  console.debug("station_url:", station_url)

  if ('mediaSession' in navigator){
    if(playing) {
      navigator.mediaSession.metadata = new MediaMetadata({
        title: station.now_playing?.song?.name || station.title,
        artist: station.now_playing?.song?.artist.name || '',
        artwork: [
          { src: station.thumbnail_url || CONSTANTS.DEFAULT_COVER, sizes: '512x512', type: 'image/png' },
        ]
      });
    } else {
      navigator.mediaSession.metadata = new MediaMetadata({});
    }
  }

  // TODO: add a retry mechanism

  // TODO: make the volume slider wider
  // TODO: when the user click play, increase the number of listeners by 1
  // Also, delay the updated by 500 ms, also optional we can add an animation when we update the listeners counter.. to emphasis it
  // TODO: make the player mobile responsive

  return (
      <div className={styles.contentHeaderLeft}>
        <div className={styles.container}>
          <img
            className={styles.songImage}
            src={station.thumbnail_url || CONSTANTS.DEFAULT_COVER}
            alt={station.title}
          />
          <div className={styles.descriptionSong}>
            <h2 className={styles.songName}>
              {station.now_playing?.song?.name}
            </h2>
            <h3 className={styles.artist}>
              {station.now_playing?.song?.artist.name}
            </h3>
            <div className={styles.playerContainer}>
              <button onClick={() => {
                setPlaying(!playing);
              }}>{playing? 'Stop': 'Start'}</button>

              {/* TODO: we might replace this with a more intuitive component.. */}
              <InputRange
                step={1}
                maxValue={100}
                minValue={0}
                value={volume}
                formatLabel={value => ''}
                onChange={value => {
                  setVolume(value as number)
                }} />
              <div className={styles.playerContainer}>
                {useMemo(() => {
                  return (
                    <ReactPlayer
                      url={playing? station_url: ''}
                      playing={playing}
                      // controls={true}
                      volume={volume/100}
                      onPause={() => {
                        console.log("pause")
                      }}
                      onReady={(r) => {
                        console.log("ready")
                      }}
                      onEnded={() => {
                        console.log("onEnded")
                      }}
                      onError={(e) => {
                        console.error(e);
                       if(!retryMechanism()) {
                         setPlaying(false);
                       }
                      }}
                      config={{
                        file: {
                          attributes: {
                            autoPlay: false
                          },
                          forceAudio: true
                        }
                      }}
                    />
                  );
                }, [station.id, station_url, playing, volume])}

            </div>
          </div>
        </div>
      </div>
      </div>
  );
}
