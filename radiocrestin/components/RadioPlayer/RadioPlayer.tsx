import React, { useEffect, useRef } from "react";
import PlyrJS from "plyr";
import Plyr from "plyr-react";
import styles from "./RadioPlayer.module.scss"
import castTV from '../../public/images/castTV.svg'
import imgSong from '../../public/images/image-008.jpg'

export default function RadioPlayer(props: any) {
    const playingStation = props.station;

    let remaining_retries = 5;
    let remaining_error_retries = 5;

    const playerRef = useRef()
    useEffect(() => {
        // @ts-ignore
        if(typeof playerRef?.current?.plyr?.id === "undefined") {
            return
        }

        // @ts-ignore
        const player = playerRef.current.plyr;
        let stoppedByError = false;

        if(typeof player?.config?.title === "undefined") {
            player.stop();

        } else {
            player.play();
            stoppedByError = false;
        }
        player.on('pause', function() {
            if(!stoppedByError) {
                props.onStationStopped();
            }
        });
        player.on('loadeddata', function() {
            // player.elements.display.currentStation.textContent = player.config.title;
        });
        player.on('waiting', function() {
            // player.elements.display.currentStation.textContent = 'Se incarca..';
        });
        player.on('stalled', function() {
            // alert('A aparut o problema neasteptata. Va rugam incercati mai tarziu!')
            stoppedByError = true;
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
            stoppedByError = true;
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
  return <>

    <div className={styles.containerPlayer}>
      <div className={styles.descriptionSong}>
        <img className={styles.castTVImg}  src={castTV.src} alt="cast icon"/>
        <h4 className={styles.radioName}>Aripi spre cer</h4>
        <h2 className={styles.nameSong}>Sunt iubit</h2>
        <h3 className={styles.artist}> Silo</h3>

        <div className={styles.containerPlyr}>
          <Plyr
            // @ts-ignore
            ref={ playerRef }
            source={ playerSrc }
            options={
              {
                debug: false,
                settings: ['quality'],
                autoplay: true,
                volume: 0.8,
                resetOnEnd: true,
                invertTime: false,
                controls: ['play', 'current-station1', 'current-time', 'mute', 'volume', 'pip', 'airplay'],
              }
            }/>
        </div>

      </div>
      <div className={styles.imageSong}>
        <img src={imgSong.src} />
      </div>
    </div>
  </>
}
