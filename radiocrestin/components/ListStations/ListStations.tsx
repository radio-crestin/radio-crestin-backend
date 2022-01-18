import React from "react";
import Station from "@/components/ListStations/Station/Station";
import styles from "./ListStations.module.scss"

export default function ListStations() {
  return <div className={`container`}>
    <div className={styles.category}>
      <div className={styles.categoryName}>General</div>
      <div className={styles.listStations}>
        <Station />
        <Station />
        <Station />
        <Station />
        <Station />
      </div>
    </div>

    <div className={styles.category}>
      <div className={styles.categoryName}>Muzică</div>
      <div className={styles.listStations}>
        <Station />
        <Station />
        <Station />
        <Station />
        <Station />
      </div>
    </div>
  </div>
}
