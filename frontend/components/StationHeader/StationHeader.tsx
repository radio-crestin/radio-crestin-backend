import React, { useEffect, useState } from "react";

import InviteButton from "@/components/InviteButton/InviteButton";
import RandomStationButton from "@/components/RandomStationButton/RandomStationButton";
import StationInformation from "@/components/StationInformation/StationInformation";
import styles from "./StationHeader.module.scss";
import dynamic from "next/dynamic";
import { useStations } from "../../hooks/stations";
import Circle_matrix_desktop from "@/public/circle_matrix_desktop.svg";
import { Station } from "../../types";

export const StationPlayer = dynamic(
  () => import("components/StationPlayer/StationPlayer"),
  {
    ssr: true,
  },
);

export default function StationHeader(station: Station) {
  const [showChild, setShowChild] = useState(false);
  const [started, setStarted] = useState(false);

  useEffect(() => {
    setShowChild(true);
  }, []);

  if (!showChild) {
    return null;
  }

  return (
    <div className={styles.header}>
      <div className={styles.row}>
        <InviteButton />
        <RandomStationButton />
      </div>
      <div className={styles.currentStation}>
        <StationPlayer
          key={station?.id}
          station={station}
          started={started}
          onStop={() => setStarted(false)}
        />
        <StationInformation station={station} />
        <img
          className={styles.matrix}
          src={Circle_matrix_desktop.src}
          alt={"fullSymbol"}
        />
      </div>
    </div>
  );
}
