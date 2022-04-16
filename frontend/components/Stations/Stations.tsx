import styles from "./Stations.module.scss";
import React from "react";
import { Station } from "types";
import {CONSTANTS} from "../../lib/constants";

const Station = (station: Station) => {
  return (
    <div className={styles.station}>
      <img
        className={`${styles.station_Image} ${
          !station?.uptime?.is_up && styles.is_Offline
        }`}
        src={station.thumbnail_url || CONSTANTS.DEFAULT_COVER}
        alt="Image station"
        loading={"lazy"}
      />
      <div className={styles.station_Label}>{station.title}</div>
    </div>
  );
};

interface IProps {
  stations: Array<Station>;
  onStationSelect: (station: Station) => void;
}

export default function Stations(props: IProps) {
  const { stations } = props;
  stations.sort((a, b) => (a.id > b.id ? -1 : 1));

  return (
    <>
      <div className={styles.container}>
        {Object.values(stations).map((station: Station): any => (
          <div key={station.id} onClick={() => props.onStationSelect(station)}>
            <Station {...station} />
          </div>
        ))}
      </div>
    </>
  );
}
