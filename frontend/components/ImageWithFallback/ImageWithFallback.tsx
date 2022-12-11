import {useEffect, useState} from 'react';

import Image from 'next/image';
import {cdnImageLoader} from '@/utils/cdnImageLoader';
import {ImageProps} from 'next/dist/client/image';

export const ImageWithFallback = ({
  fallbackSrc,
  ...props
}: ImageProps & {fallbackSrc: string}) => {
  const [error, setError] = useState(false);

  useEffect(() => {
    setError(false);
  }, [props.src]);

  return (
    <Image
      {...{
        loader: cdnImageLoader,
        onError: () => setError(true),
        ...props,
        src: error ? fallbackSrc : props.src,
      }}
      draggable={false}
    />
  );
};
