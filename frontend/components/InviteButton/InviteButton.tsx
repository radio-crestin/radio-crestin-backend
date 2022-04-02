import React from "react";

import styles from './InviteButton.module.scss'
export default function InviteButton(props: any) {
  return <a href="#invite" target="_blank" className={styles.inviteButton}>
      Invita un prieten
  </a>
}
