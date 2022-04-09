import React from "react";

import styles from './RandomStationButton.module.scss'
export default function RandomStationButton(props: any) {
  return <a href="#random-station" target="_blank" className={styles.randomStationButton}>
    <svg
      width="31" height="31"
      focusable="false" aria-hidden="true" viewBox="0 0 24 24"
      data-testid="ElectricBoltIcon">
      <path
  fill="white"
  d="M14.69 2.21 4.33 11.49c-.64.58-.28 1.65.58 1.73L13 14l-4.85 6.76c-.22.31-.19.74.08 1.01.3.3.77.31 1.08.02l10.36-9.28c.64-.58.28-1.65-.58-1.73L11 10l4.85-6.76c.22-.31.19-.74-.08-1.01-.3-.3-.77-.31-1.08-.02z"/>
    </svg>

  </a>
}
