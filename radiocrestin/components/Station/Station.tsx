import React from "react";
import styles from "./Station.module.scss"
import NumberOfListeners from "@/components/NumberOfListeners";
import { StationData } from "../../types";
import Image from "next/image";

export default function Station(props: { station: StationData, onSelect: (stationData: StationData) => void, isSelected: boolean }) {
  // TODO: adjust the font size when there is no station.title and station.artist (eg. Radio Micul Samaritean)
  // TODO: make the thumbnail unmovable
  // TODO: add an indicator when the station is playing like is on Spotify..
  // https://icons8.com/animated-icons/set/player
  // You can use this lib to convert LottieFile to svg https://github.com/chadly/lottie-to-svg

  return <>
    <div className={ styles.containerStation }
         onClick={ (e) => props.onSelect(props.station) }>
      <div className={ styles.stationName }>{ props.station.title }</div>
      <div className={`${styles.stationImageContainer} ${props.isSelected && styles.isSelected}`}>
        <Image
          src={ props.station.thumbnail_url }
          layout={ 'responsive' }
          objectFit={ 'cover' }
          alt={ props.station.title }
          width={ '100%' }
          height={ '100%' }
          className={ styles.stationImage }
        />
        <div className={ styles.numberOfListeners }>
          <NumberOfListeners listeners={ props.station.stats?.listeners }/>
        </div>
        <div className={ styles.stationSong }>
          <p className={ styles.songName }
             title={ props.station.stats?.current_song?.songName }>
            { props.station.stats?.current_song?.songName }
          </p>
          <p className={ styles.songArtist }
             title={ props.station.stats?.current_song?.artist }>
            { props.station.stats?.current_song?.artist }
          </p>
        </div>
      </div>
    </div>
  </>
}
