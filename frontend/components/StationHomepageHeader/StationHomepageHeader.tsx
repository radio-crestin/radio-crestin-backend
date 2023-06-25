import React from 'react';

import StationInformation from '@/components/StationInformation/StationInformation';
import {Box, Flex} from '@chakra-ui/react';
import SongInformation from '@/components/SongInformation/SongInformation';
import {Station} from '../../types';
import {ArrowBackIcon, ArrowForwardIcon} from '@chakra-ui/icons';

export default function StationHomepageHeader({
  selectedStation,
}: {
  selectedStation: Station;
}) {
  return (
    <Flex
      borderRadius={{base: 12, lg: 40}}
      mx={{base: -2, lg: 'auto'}}
      mb={{base: 0, lg: 12}}
      px={{base: 3, lg: 8}}
      py={{base: 3, lg: 14}}
      bg={'brand.600'}
      flexDirection={{base: 'column-reverse', lg: 'row'}}>
      <Box display={'flex'} alignItems={'center'}>
        <ArrowBackIcon
          margin={2}
          cursor={'pointer'}
          height="50px"
          width="50px"
          padding={'5px'}
          borderRadius={30}
          color={'black'}
          border={'2px solid black'}
        />
      </Box>
      <SongInformation key={selectedStation?.id} station={selectedStation} />
      <Box
        w={{base: '100%', lg: '71%'}}
        minW={{base: 'auto', lg: '400px'}}
        pl={{base: 1, lg: 4}}>
        <StationInformation station={selectedStation} />
      </Box>
      <Box display={'flex'} alignItems={'center'}>
        <ArrowForwardIcon
          margin={2}
          cursor={'pointer'}
          height="50px"
          width="50px"
          padding={'5px'}
          borderRadius={30}
          color={'black'}
          border={'2px solid black'}
        />
      </Box>
    </Flex>
  );
}
