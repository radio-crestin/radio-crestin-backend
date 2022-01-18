import styles from './Header.module.scss'
import logoImg from 'public/images/Logo.svg'
import RadioPlayer from "./RadioPlayer/RadioPlayer";

export default function Header() {

  return <>
    <div className={ `container ${ styles.containerBackground }` }>
      <div className={ `${ styles.titleLogo }` }>
        <img src={ logoImg.src } alt={ 'logo img' }/>
        <h1 className={ `${ styles.title }` }>Radio Creștin</h1>
      </div>

      <div className={`${styles.contentBottom}`}>
        <div className={`${styles.welcome}`}>
          <h1 className={styles.goodMorning}>Bună dimineața!</h1>
          <h4 className={`${styles.verseOfDay}`}>Ferice de cei ce plâng, căci ei vor fi mângâiaţi! MATEI 5:4</h4>
        </div>
        <div className={`${styles.radioPlayer}`}>
          <RadioPlayer />
        </div>
      </div>
    </div>
  </>
}
