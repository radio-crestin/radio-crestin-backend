import React from "react";
import stationIMG from "public/images/image-023.png";
import styles from "./Station.module.scss"
import NumberOfListeners from "@/components/NumberOfListeners";

export default function Station() {
  return <>
    <div className={styles.containerStation}>
      <img className={styles.stationImage} src={ stationIMG.src } alt={ 'logo img' }/>
      <div className={styles.numberOfListeners}>
        <NumberOfListeners />
      </div>
      <div className={styles.stationName}>RVE Bucuresti</div>
      <div className={styles.stationSong}>Sunt iubit - Silo</div>
    </div>
  </>
}
