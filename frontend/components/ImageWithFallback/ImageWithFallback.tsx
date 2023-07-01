import {useEffect, useState} from 'react';

import {cdnImageLoader} from '@/utils/cdnImageLoader';
import {Image} from '@chakra-ui/react';
import {ImageProps} from '@chakra-ui/image';

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
      {...props}
      onError={() => setError(true)}
      htmlHeight={250}
      htmlWidth={250}
      loading={'lazy'}
      src={cdnImageLoader({
        src: error ? fallbackSrc : props.src,
        width: 256,
      })}
      draggable={false}
    />
  );
};
