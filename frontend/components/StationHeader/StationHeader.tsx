import React from "react";

import InviteButton from "@/components/InviteButton/InviteButton";
import RandomStationButton from "@/components/RandomStationButton/RandomStationButton";
import StationInformation from "@/components/StationInformation/StationInformation";
import styles from "./StationHeader.module.scss";

export default function StationHeader(props: any) {
  console.log("props", props);
  return (
    <div className={styles.header}>
      <div className={styles.row}>
        <InviteButton />
        <RandomStationButton />
      </div>
      <div className={styles.currentStation}>
        {/*<StationPlayer/>*/}
        <div style={{ width: "50%" }}>Content left</div>
        <StationInformation />
      </div>
    </div>
  );
}
