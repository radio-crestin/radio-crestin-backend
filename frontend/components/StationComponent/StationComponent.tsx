import React from "react";
import styles from "./Station.module.scss"
import NumberOfListeners from "@/components/NumberOfListeners";
import {Station} from "../../types";

export default function StationComponent(props: { station: Station, onSelect: (Station: Station) => void }) {
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
          listeners={props.station.now_playing?.listeners}
          isUp={props.station.uptime?.up}/>
      </div>
      <div className={styles.stationName}>{props.station.title}</div>
      <div
        className={styles.stationSong}>
        {props.station.now_playing?.song?.name}
        {props.station.now_playing?.song?.artist ? "- " + props.station.now_playing?.song?.artist : ""}
      </div>
    </div>
  </>
}
