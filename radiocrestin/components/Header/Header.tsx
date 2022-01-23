import styles from './Header.module.scss'
import {ReactChild, ReactFragment, ReactPortal} from 'react';
import Image from 'next/image'

export default function Header(props: { children: boolean | ReactChild | ReactFragment | ReactPortal | null | undefined; }) {

  return <>
    <div className={`${styles.header}`}>
      <Image
        src={require('../../public/images/header-bg.jpg')}
        className={styles.headerImage}
        layout={'fill'}
        objectFit={'cover'}
        alt="Background header img."
        priority={ true }
      />
      {props.children}
    </div>
  </>
}
