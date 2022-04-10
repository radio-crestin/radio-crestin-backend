import React from "react";
import Rating from "react-rating";

import styles from "./StationInformation.module.scss";

import Star from "@/public/Star.svg";
import StarRed from "@/public/Star_red.svg";
import StarGray from "@/public/Star_gray.svg";
import FacebookIcon from "@/public/facebook.svg";
import Link from "@/public/link.svg";

export default function StationInformation(props: any) {
  const { station } = props;
  const StationRating = 4.5;
  const NumberOfListeners = station.now_playing.listeners;
  const ReadMoreLink = "https://www.facebook.com/";

  const onRatingChange = (rating: number) => {
    console.log("rating = ", rating);
  };

  return (
    <div className={styles.container}>
      <h1 className={styles.station_Name}>{station.title}</h1>

      <div className={styles.station_RatingContainer}>
        {/*@ts-ignore*/}
        <Rating
          onChange={rating => onRatingChange(rating)}
          placeholderRating={StationRating}
          emptySymbol={
            <img
              src={StarGray.src}
              height={22}
              width={22}
              alt={"empty symbol"}
            />
          }
          placeholderSymbol={
            <img
              src={Star.src}
              height={22}
              width={22}
              alt={"placeholder symbol"}
            />
          }
          fullSymbol={
            <img src={StarRed.src} height={22} width={22} alt={"fullSymbol"} />
          }
        />
        {/*@ts-ignore*/}
        {StationRating !== 0 && (
          <p className={styles.rating}>{StationRating}/5</p>
        )}
        <img
          src={FacebookIcon.src}
          className={styles.facebookIcon}
          alt={"facebook icon"}
          height={22}
          width={22}
        />
      </div>

      {/*@ts-ignore*/}
      {NumberOfListeners && (
        <p className={styles.station_NumberOfListeners}>
          {NumberOfListeners} persoane ascultă împreună cu tine
        </p>
      )}
      <p className={styles.station_Quote}>
        ”Nu numai că trebuie să ne ferim să producem dezbinare, ci trebuie să
        devenim agenți ai păcii, străduindu-ne să reconciliem părțile aflate în
        conflict.” – Deborah Smith Pegues
      </p>
      <a
        type="button"
        className={styles.station_ReadMore}
        href={ReadMoreLink}
        target={"_blank"}>
        Continuă citirea articolului “Limba care dezbină”
        <img src={Link.src} alt={"link symbol"} height={22} width={22} />
      </a>
    </div>
  );
}
