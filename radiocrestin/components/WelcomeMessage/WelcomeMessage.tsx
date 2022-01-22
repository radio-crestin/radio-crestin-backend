import React from "react";
import styles from "@/components/Header/Header.module.scss";

export default function WelcomeMessage() {

  return <>
    <div className={`${styles.contentBottom}`}>
      <div className={`${styles.welcome}`}>
        <h1 className={styles.goodMorning}>Bună dimineața!</h1>
        <h4 className={`${styles.verseOfDay}`}>Ferice de cei ce plâng, căci ei
          vor fi mângâiaţi! MATEI 5:4</h4>
      </div>
    </div>
  </>
}
