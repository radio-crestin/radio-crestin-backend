import React from "react";
import styles from "./StationInformation.module.scss";
import RatingStation from "@/components/RatingStation/RatingStation";

export default function StationInformation(props: any) {
  return (
    <div className={styles.container}>
      <h1>Aripi spre cer</h1>
      <RatingStation
        faceBookLink={"https://www.facebook.com/elisei.nicolae"}
        ratingNumber={5}
      />
      <p>50 de persoane ascultă împreună cu tine</p>
      <p>
        Nu numai că trebuie să ne ferim să producem dezbinare, ci trebuie să
        devenim agenți ai păcii, străduindu-ne să reconciliem părțile aflate în
        conflict.” – Deborah Smith Pegues
      </p>
      <p>Continuă citirea articolului “Limba care dezbină”</p>
    </div>
  );
}
