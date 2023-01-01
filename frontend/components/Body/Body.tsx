import {ReactChild, ReactFragment, ReactPortal, useEffect} from "react";

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
  useEffect(() => {
    window.addEventListener("load", function () {
      navigator.serviceWorker?.register("/sw.js").then(
        function (registration) {
          console.log(
            "Service Worker registration successful with scope: ",
            registration.scope
          );
        },
        function (err) {
          console.error("Service Worker registration failed: ", err);
        }
      );
    });
  });
  return <div className={styles.body}>{props.children}</div>;
}
