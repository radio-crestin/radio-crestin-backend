import React, { useEffect, useState } from "react";

import InviteButton from "@/components/InviteButton/InviteButton";
import RandomStationButton from "@/components/RandomStationButton/RandomStationButton";
import StationInformation from "@/components/StationInformation/StationInformation";
import styles from "./StationHeader.module.scss";
import dynamic from "next/dynamic";
import Circle_matrix_desktop from "@/public/circle_matrix_desktop.svg";
import Circle_matrix_mobile from "@/public/circle_matrix_mobile.svg";
import { Station } from "../../types";
import useWindowSize from "../../hooks/useWindowSize";

export const StationPlayer = dynamic(
  () => import("components/StationPlayer/StationPlayer"),
  {
    ssr: true,
  },
);

export default function StationHeader(station: Station) {
  const [showChild, setShowChild] = useState(false);
  const [started, setStarted] = useState(true);
  const window = useWindowSize();

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
        {window.width > 767 && <RandomStationButton />}
      </div>
      <div className={styles.currentStation}>
        <StationPlayer
          key={station?.id}
          station={station}
          started={started}
          onStop={() => setStarted(false)}
        />
        <picture>
          <source
            media="(max-width: 1023px)"
            srcSet={Circle_matrix_mobile.src}></source>
          <source
            media="(min-width: 1024px)"
            srcSet={Circle_matrix_desktop.src}></source>
          <img
            src={Circle_matrix_desktop.src}
            className={styles.matrix}
            alt="fullSymbol"
          />
        </picture>
        <StationInformation station={station} />
      </div>
    </div>
  );
}
