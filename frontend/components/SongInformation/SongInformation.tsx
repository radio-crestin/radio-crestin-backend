import React from 'react';
import {Station} from '../../types';
import {CONSTANTS} from '../../lib/constants';
import {Box, Flex, Text} from '@chakra-ui/react';
import {
  ImageWithFallback
} from '@/components/ImageWithFallback/ImageWithFallback';

export default function SongInformation(props: { station: Station }) {
  const {station} = props;

  return (
    <Box
      w={{base: '29%'}}
      h={{base: '360px'}}
      minW={{base: '250px'}}
      maxW={'100%'}
      pl={{base: 4}}
      position={{base: 'relative'}}
      bottom={{base: 'auto'}}
      left={{base: 'auto'}}
      right={{base: 'auto'}}
      display={{base: 'none', lg: 'block'}}
      zIndex={9}>
      <Box
        bg={{base: 'transparent'}}
        borderRadius={15}
        m={{base: 0}}
        p={{base: 0}}
        mt={{base: 6}}
        display={{base: 'block'}}
        alignItems={{base: 'auto'}}>
        <Box
          overflow={'hidden'}
          style={{
            filter: 'drop-shadow(2px 2px 5px rgba(0, 0, 0, 0.25))',
          }}
          height={250}
          width={250}>
          <ImageWithFallback
            src={
              station.now_playing?.song?.thumbnail_url ||
              station.thumbnail_url ||
              CONSTANTS.DEFAULT_COVER
            }
            fallbackSrc={station.thumbnail_url || CONSTANTS.DEFAULT_COVER}
            alt={`${station.title} | Radio Crestin`}
            loading={'eager'}
            style={{
              filter: station?.uptime?.is_up ? 'unset' : 'grayscale(1)',
              objectFit: 'cover',
              width: '100%',
              height: '100%',
            }}
          />
        </Box>
        <Flex
          w={'100%'}
          mt={{base: 3}}
          ml={{base: 0}}
          flexDirection={{base: 'column'}}>
          <Box>
            <Text
              as="h2"
              fontSize={{base: '2xl'}}
              mt={{base: 2}}
              lineHeight={1.3}
              color={{base: 'gray.800'}}
              noOfLines={2}
              fontWeight="700">
              {station.now_playing?.song?.name || (
                <Box display={{base: 'none'}}>{station.title}</Box>
              )}
            </Text>
            <Text
              as="h3"
              fontSize={{base: 'base'}}
              color={{base: 'gray.800'}}
              noOfLines={1}>
              {station.now_playing?.song?.artist.name}
            </Text>
          </Box>
        </Flex>
      </Box>
    </Box>
  );
}
