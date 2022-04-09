import Image from "next/image";

import styles from "./Stations.module.scss";
import DefaultStationImage from "@/public/images/default-station-thumbnail.png";
import React from "react";

const isOffline = false;

const Station = () => {
  return (
    <div className={styles.station}>
      <div
        className={`${styles.station_Image} ${isOffline && styles.is_Offline}`}>
        <Image
          className={styles.songImage}
          src={DefaultStationImage.src}
          layout={"fill"}
          objectFit={"contain"}
          alt="Image station"
        />
      </div>
      <div className={styles.station_Label}>Aripi Spre Cer General</div>
    </div>
  );
};

export default function Stations() {
  return (
    <>
      <div className={styles.container}>
        <Station />
        <Station />
        <Station />
        <Station />
        <Station />
        <Station />
        <Station />
      </div>
    </>
  );
}
