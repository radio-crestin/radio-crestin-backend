import React from "react";
import InviteButton from "@/components/InviteButton/InviteButton";
import RandomStationButton
  from "@/components/RandomStationButton/RandomStationButton";
import styles from './StationHeader.module.scss'
import {StationPlayer} from "../../pages";
import StationInformation
  from "@/components/StationInformation/StationInformation";
import RadioPlayer from "@/components/RadioPlayer/RadioPlayer";

export default function StationHeader(props: any) {
  console.log('props', props);
  return <div className={styles.header}>
    <div className={styles.row}>
      <InviteButton />
      <RandomStationButton/>
    </div>
    <div className={styles.row}>
      {/*<StationPlayer/>*/}
      <StationInformation/>
    </div>

  </div>
}
