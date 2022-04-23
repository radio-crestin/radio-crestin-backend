import React, {useMemo, useState} from "react";
import styles from "./StationPlayer.module.scss";
import { Station } from "../../types";
import {CONSTANTS} from "../../lib/constants";
import ReactPlayer from "react-player";
import InputRange from "react-input-range";

import 'react-input-range/lib/css/index.css'

let firstStart = true;

export default function StationPlayer(props: {
  station?: Station;
}) {
  const { station } = props;
  if (typeof station === "undefined") {
    return <></>;
  }

  const [playing, setPlaying] = useState(!firstStart);
  firstStart = false;

  // TODO: we might need to populate these from local storage
  const [volume, setVolume] = useState(60);


  // TODO: add a retry mechanism

  // TODO: make the volume slider wider
  // TODO: when the user click olaying, increase the number of listeners by 1 so that he can see that
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
                step={5}
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
                      url={playing? station?.stream_url: ''}
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
                      onError={(e, p) => {
                        console.error(e, p);
                        setPlaying(false);
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
                }, [station.id, playing])}

            </div>
          </div>
        </div>
      </div>
      </div>
  );
}
