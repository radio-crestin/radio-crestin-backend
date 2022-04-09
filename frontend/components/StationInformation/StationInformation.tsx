import React from "react";
import styles from "./StationInformation.module.scss";
import Rating from "react-rating";
import Star from "@/public/Star.svg";
import StarRed from "@/public/Star_red.svg";
import StarGray from "@/public/Star_gray.svg";
import FacebookIcon from "@/public/facebook.svg";
import Link from "@/public/link.svg";

export default function StationInformation(props: any) {
  const StationRating = 4.2;
  const NumberOfListeners = 25;
  const ReadMoreLink = "https://www.facebook.com/";

  const onRatingChange = (rating: number) => {
    console.log("rating = ", rating);
  };

  return (
    <div className={styles.container}>
      <h1 className={styles.station_Name}>Aripi spre cer</h1>

      <div className={styles.station_RatingContainer}>
        <Rating
          onChange={rating => onRatingChange(rating)}
          placeholderRating={StationRating}
          emptySymbol={<img src={StarGray.src} alt={"empty symbol"} />}
          placeholderSymbol={<img src={Star.src} alt={"placeholder symbol"} />}
          fullSymbol={<img src={StarRed.src} alt={"fullSymbol"} />}
        />
        {StationRating !== 0 && (
          <p className={styles.rating}>{StationRating}/5</p>
        )}
        <img
          src={FacebookIcon.src}
          className={styles.facebookIcon}
          alt={"empty symbol"}
        />
      </div>

      {NumberOfListeners !== 0 && (
        <p className={styles.station_NumberOfListeners}>
          {NumberOfListeners} de persoane ascultă împreună cu tine
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
        <img
          src={Link.src}
          className={styles.facebookIcon}
          alt={"empty symbol"}
        />
      </a>
    </div>
  );
}
