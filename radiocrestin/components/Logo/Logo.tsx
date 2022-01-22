import React from "react";
import styles from "@/components/Header/Header.module.scss";
import logoImg from "@/public/images/Logo.svg";

export default function Logo() {

  return <>
    <div className={`${styles.titleLogo}`}>
      <img src={logoImg.src} alt={'logo img'}/>
      <h1 className={`${styles.title}`}>Radio Crestin</h1>
    </div>
  </>
}
