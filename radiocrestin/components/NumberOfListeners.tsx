import React from "react";
import headphone from "@/public/images/headphone.svg";

export default function NumberOfListeners({
                                            listeners,
                                            isUp
                                          }: { listeners?: number | null, isUp?: boolean }) {
  return <>
    <div style={{
      display: "flex",
      alignItems: "center",
      gap: "0 5px",
      padding: "5px 7px",
      background: isUp || typeof isUp === "undefined" ? "#020202a6" : "#7a7a7ab3",
      width: "fit-content",
      borderRadius: "20px"
    }}>
      <img src={headphone.src} alt="cast icon"/>
      {listeners && (<p style={{color: "white", fontSize: 15}}>{listeners}</p>)}

    </div>
  </>
}
