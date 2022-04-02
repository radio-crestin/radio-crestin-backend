import React from "react";
import InviteButton from "@/components/InviteButton/InviteButton";
import RandomStationButton
  from "@/components/RandomStationButton/RandomStationButton";
import styles from './StationHeader.module.scss'
import {StationPlayer} from "../../pages";
import StationInformation
  from "@/components/StationInformation/StationInformation";

export default function StationHeader(props: any) {
  return <div className={styles.header}>
    <div className={styles.row}>
      <InviteButton />
      <RandomStationButton/>
    </div>
    <div className={styles.row}>
      <StationPlayer/>
      test
      <StationInformation/>
    </div>

  </div>
}
