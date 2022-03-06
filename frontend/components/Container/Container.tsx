import React from "react";
import styles from './Container.module.scss'

export default function Container(props: { children: any; }) {
  return <div className={styles.container}>
    {props.children}
  </div>
}
