import React from "react";
import styles from "./Station.module.scss"
import NumberOfListeners from "@/components/NumberOfListeners";
import {StationData} from "../../types";

export default function Station(props: { stationData: StationData, onSelect: (stationData: StationData) => void }) {
  // TODO: call onSelect when the user clicks on the station
  return <>
    <div className={styles.containerStation}>
      <img className={styles.stationImage} src={props.stationData.thumbnail_url}
           alt={props.stationData.title}/>
      <div className={styles.numberOfListeners}>
        <NumberOfListeners/>
      </div>
      <div className={styles.stationName}>{props.stationData.title}</div>
      <div className={styles.stationSong}>Sunt iubit - Silo</div>
    </div>
  </>
}
