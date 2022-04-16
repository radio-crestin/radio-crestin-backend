import React, { useEffect, useMemo, useRef } from "react";
import PlyrJS from "plyr";
import Plyr from "plyr-react";
import styles from "./StationPlayer.module.scss";
import { Station } from "../../types";
import Image from "next/image";
import {CONSTANTS} from "../../lib/constants";

export default function StationPlayer(props: {
  station?: Station;
  started: boolean;
  onStop: () => void;
}) {
  // const startPlaying = props.startPlaying;
  if (typeof props.station === "undefined") {
    return <></>;
  }
  let remaining_retries = 5;
  let remaining_error_retries = 5;
  const { station } = props;

  const playerRef = useRef();
  useEffect(() => {
    // @ts-ignore
    if (typeof playerRef?.current?.plyr?.id === "undefined") {
      console.log("Player is undefined");
      return;
    }

    // @ts-ignore
    const player = playerRef.current.plyr;
    let stoppedByError = false;

    if (props.station && props.started) {
      console.log("Starting the player..");
      player.play();
      stoppedByError = false;
    } else {
      console.log("Stoping the player..");
      player.stop();
    }
    player.on("pause", function () {
      if (!stoppedByError) {
        props.onStop();
      }
    });
    player.on("loadeddata", function () {
      // player.elements.display.currentStation.textContent = player.config.title;
    });
    player.on("waiting", function () {
      // TODO: display this somewhere..
      // player.elements.display.currentStation.textContent = 'Se incarca..';
    });
    player.on("stalled", function () {
      // alert('A aparut o problema neasteptata. Va rugam incercati mai tarziu!')
      stoppedByError = true;
      console.log("Pausing the player..");
      player.pause();
      console.trace("stalled", event);
      if (props.station && remaining_retries > 0) {
        setTimeout(
          function () {
            console.log("Retrying to play..");
            // player.source = lastPlayerSource;
            player.play();
            remaining_retries--;
          },
          remaining_retries === 5 ? 0 : 1000,
        );
      }
    });
    player.on("error", function (event: any) {
      stoppedByError = true;
      console.trace("error", event);
      if (
        !player.media.paused &&
        event.detail.plyr.media.error &&
        event.detail.plyr.failed &&
        remaining_error_retries > 0
      ) {
        setTimeout(
          function () {
            console.log("Retrying to play..");
            // player.source = lastPlayerSource;
            player.play();
            remaining_error_retries--;
          },
          remaining_error_retries === 5 ? 0 : 1000,
        );
      }
    });
  }, [props.station.id]);

  const playerSrc: PlyrJS.SourceInfo = {
    type: "audio",
    title: props.station.title,
    sources: [
      {
        src: props.station.stream_url,
        type: "audio/mp3",
      },
    ],
  };
  // TODO: make the volume slider wider
  // TODO: when the user click play, increase the number of listeners by 1 so that he can see that
  // Also, delay the updated by 500 ms, also optional we can add an animation when we update the listeners counter.. to emphasis it
  // TODO: make the player mobile responsive
  // TODO: normalize the sound volume (100% - 10db, 70% - 7db, etc)

  return (
    <>
      <div className={styles.contentHeaderLeft}>
        <div className={styles.container}>
          <img
            className={styles.songImage}
            src={station.thumbnail_url || CONSTANTS.DEFAULT_COVER}
            alt="Image station"
          />
          <div className={styles.descriptionSong}>
            <h2 className={styles.songName}>
              {station.now_playing?.song?.name}
            </h2>
            <h3 className={styles.artist}>
              {station.now_playing?.song?.artist.name}
            </h3>
            <div className={styles.containerPlyr}>
              {useMemo(() => {
                return (
                  <Plyr
                    // @ts-ignore
                    ref={playerRef}
                    source={playerSrc}
                    options={{
                      debug: false,
                      settings: ["quality"],
                      autoplay: props.started,
                      volume: 0.8,
                      resetOnEnd: true,
                      invertTime: false,
                      controls: [
                        "play",
                        "current-station1",
                        "current-time",
                        "mute",
                        "volume",
                        "pip",
                        "airplay",
                      ],
                    }}
                  />
                );
              }, [props.station.id])}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
