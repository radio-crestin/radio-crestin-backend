import React from 'react';
import {Box, Text} from '@chakra-ui/react';

import {Station} from '../../types';

export default function StationMetadata(station: Station) {
  return (
    <Box>
      {station.now_playing?.song?.name && (
        <Text
          as={'h4'}
          position={'absolute'}
          bottom={'110px'}
          py={1}
          px={1}
          fontSize="md"
          color={'white'}
          align={'left'}
          fontWeight={'600'}
          noOfLines={1}
          background={'black'}
          opacity={0}
          transition={'opacity .2s linear'}
          _groupHover={{opacity: 1}}>
          {station.now_playing?.song?.name}
        </Text>
      )}
      {station.now_playing?.song?.artist.name && (
        <Text
          as={'h5'}
          position={'absolute'}
          bottom={'87px'}
          py={0}
          px={1}
          fontSize="0.73rem"
          color={'white'}
          align={'left'}
          fontWeight={'400'}
          noOfLines={1}
          background={'black'}
          opacity={0}
          transition={'opacity .2s linear'}
          _groupHover={{opacity: 1}}>
          {station.now_playing?.song?.artist.name}
        </Text>
      )}
    </Box>
  );
}
