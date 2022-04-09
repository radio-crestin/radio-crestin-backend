import {ReactChild, ReactFragment, ReactPortal} from "react";

import styles from './Body.module.scss'

export default function Body(props: { children: boolean | ReactChild | ReactFragment | ReactPortal | null | undefined; }) {

  return <body className={styles.body}>
    {props.children}
  </body>
}
