import { ReactChild, ReactFragment, ReactPortal } from "react";

import styles from "./Body.module.scss";

export default function Body(props: {
  children:
    | boolean
    | ReactChild
    | ReactFragment
    | ReactPortal
    | null
    | undefined;
}) {
  return <div className={styles.body}>{props.children}</div>;
}
