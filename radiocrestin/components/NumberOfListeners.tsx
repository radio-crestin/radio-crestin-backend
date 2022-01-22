import React from "react";
import headphone from "@/public/images/headphone.svg";

export default function NumberOfListeners() {
  return <>
    <div style={{
      display: "flex",
      alignItems: "center",
      gap: "0 5px",
      padding: "5px 7px",
      background: "#020202a6",
      width: "fit-content",
      borderRadius: "20px"
    }}>
      <img src={headphone.src} alt="cast icon"/>
      <p style={{color: "white", fontSize: 15}}>120</p>
    </div>
  </>
}
