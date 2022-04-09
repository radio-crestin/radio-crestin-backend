import React from "react";
import styles from "./StationsGroup.module.scss";

export default function StationsGroup(props: { groupName: string, children: any; }) {

  return <>
    <div className={styles.container}>
      <div className={styles.name}>{props.groupName}</div>
      <div className={styles.stations}>
        {props.children}
      </div>
    </div>
  </>
}
