import React from "react";
import styles from "./Station.module.scss"
import NumberOfListeners from "@/components/NumberOfListeners";
import {StationData} from "../../types";

export default function Station(props: { station: StationData, onSelect: (stationData: StationData) => void }) {
  // TODO: adjust the font size when there is no station.title and station.artist (eg. Radio Micul Samaritean)
  // TODO: make the thumbnail unmovable
  // TODO: add an indicator when the station is playing like is on Spotify..
  // https://icons8.com/animated-icons/set/player
  // You can use this lib to convert LottieFile to svg https://github.com/chadly/lottie-to-svg
  return <>
    <div className={styles.containerStation}
         onClick={(e) => props.onSelect(props.station)}>
      <img className={styles.stationImage} src={props.station.thumbnail_url}
           alt={props.station.title}/>
      <div className={styles.numberOfListeners}>
        <NumberOfListeners
          listeners={props.station.stats?.listeners}
          isUp={props.station.uptime.up}/>
      </div>
      <div className={styles.stationName}>{props.station.title}</div>
      <div
        className={styles.stationSong}>
        {props.station.stats?.current_song?.songName}
        {props.station.stats?.current_song?.artist ? "- " + props.station.stats?.current_song?.artist : ""}
      </div>
    </div>
  </>
}
