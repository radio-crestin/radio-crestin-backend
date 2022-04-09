import React, { useState } from "react";

import InviteButton from "@/components/InviteButton/InviteButton";
import RandomStationButton from "@/components/RandomStationButton/RandomStationButton";
import StationInformation from "@/components/StationInformation/StationInformation";
import styles from "./StationHeader.module.scss";
import dynamic from "next/dynamic";
import { useStations } from "../../hooks/stations";
import { getStationsMetadata } from "../../services/stations";
import { Station, StationGroup } from "../../types";
import Circle_matrix_desktop from "@/public/circle_matrix_desktop.svg";

export const StationPlayer = dynamic(
  () => import("components/StationPlayer/StationPlayer"),
  {
    ssr: true,
  },
);
export default function StationHeader(props: any) {
  const { stations, station_groups, isLoading, isError } = useStations({
    refreshInterval: 10000,
    initialStationsMetadata: {
      station_groups: [],
      stations: [],
    },
  });
  const selectedStation = stations[0];
  const [started, setStarted] = useState(false);
  return (
    <div className={styles.header}>
      <div className={styles.row}>
        <InviteButton />
        <RandomStationButton />
      </div>
      <div className={styles.currentStation}>
        <StationPlayer
          key={selectedStation?.id}
          station={selectedStation}
          started={started}
          onStop={() => setStarted(false)}
        />
        <StationInformation />
        <img
          className={styles.matrix}
          src={Circle_matrix_desktop.src}
          alt={"fullSymbol"}
        />
      </div>
    </div>
  );
}
