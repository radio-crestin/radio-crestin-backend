import styles from 'styles/Home.module.scss';
import React from 'react';
import {useMediaQuery} from '@chakra-ui/react';

export default function EmailButton(props: any) {
  const [isTabletOrMobile] = useMediaQuery('(max-width: 1024px)');
  return (
    <a
      href="mailto:iosifnicolae2@gmail.com"
      target="_blank"
      className={styles.contactButton}
      style={{
        bottom: props.isPlaying
          ? isTabletOrMobile
            ? '93px'
            : '104px'
          : '32px',
      }}>
      <div className={styles.contactLinkButton}>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          height="30px"
          viewBox="0 0 24 24"
          width="30px"
          fill="#fff">
          <path d="M0 0h24v24H0V0z" fill="none" />
          <path d="M22 6c0-1.1-.9-2-2-2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6zm-2 0l-8 5-8-5h16zm0 12H4V8l8 5 8-5v10z" />
        </svg>
      </div>
    </a>
  );
}
