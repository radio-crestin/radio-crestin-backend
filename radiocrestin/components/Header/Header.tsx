import styles from './Header.module.scss'
import {ReactChild, ReactFragment, ReactPortal} from 'react';

export default function Header(props: { children: boolean | ReactChild | ReactFragment | ReactPortal | null | undefined; }) {

  return <>
    <div className={`${styles.header}`}>
      {props.children}
    </div>
  </>
}
