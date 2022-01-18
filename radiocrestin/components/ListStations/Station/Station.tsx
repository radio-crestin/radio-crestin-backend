import React from "react";
import stationIMG from "public/images/image-023.png";
import styles from "./Station.module.scss"

export default function Station() {
  return <>
    <div className={styles.containerStation}>
      <img className={styles.stationImage} src={ stationIMG.src } alt={ 'logo img' }/>
      <div className={styles.stationName}>RVE Bucuresti</div>
      <div className={styles.stationSong}>Sunt iubit - Silo</div>
    </div>
  </>
}
