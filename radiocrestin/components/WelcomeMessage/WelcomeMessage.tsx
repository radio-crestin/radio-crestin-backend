import React  from "react";
import styles from "@/components/Header/Header.module.scss";

function setWelcomeMessage() {
  const today = new Date();
  const curHr = today.getHours();

  if (curHr < 12) {
    return "Bună dimineața!";
  } else if (curHr < 18) {
    return "Bună ziua!";
  } else {
    return "Bună seara!";
  }
}

export default function WelcomeMessage() {
  // TODO
  // Also, we need to fetch the daily verse from an API
  return <>
    <div className={ `${ styles.contentBottom }` }>
      <div className={ `${ styles.welcome }` }>
        <h1 className={ styles.goodMorning }>{ setWelcomeMessage() }</h1>
        <h4 className={ `${ styles.verseOfDay }` }>
          Ferice de cei ce plâng, căci ei vor fi mângâiaţi! MATEI 5:4</h4>
      </div>
    </div>
  </>
}
