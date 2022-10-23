import React from 'react';
import dynamic from 'next/dynamic';
import {isMobile} from 'react-device-detect';

import {Station, StationGroup} from 'types';
import {CONSTANTS} from '../../lib/constants';
import {
  AspectRatio,
  Box,
  Center,
  Grid,
  GridItem,
  Image,
  Text,
} from '@chakra-ui/react';
import Link from 'next/link';
import {cdnImageLoader} from '../../utils/cdnImageLoader';

const StationMetadata = dynamic(
  () => import('@/components/StationMetadata/StationMetadata'),
  {ssr: false},
);

const StationItem = (station: Station) => {
  return (
    <Box position={'relative'} role="group">
      <AspectRatio position={'relative'} ratio={1}>
        <Box borderRadius={{base: '20px', lg: '41px'}}>
          <Image
            src={cdnImageLoader({
              src:
                station.now_playing?.song?.thumbnail_url ||
                station.thumbnail_url ||
                CONSTANTS.DEFAULT_COVER,
              width: 384,
              quality: 80,
            })}
            alt={`${station.title} - ${station.now_playing?.song?.name} de ${station.now_playing?.song?.artist.name}`}
            boxSize="100%"
            objectFit="cover"
            htmlHeight={250}
            htmlWidth={250}
            style={{
              filter: station?.uptime?.is_up ? '' : 'grayscale(1)',
            }}
          />
        </Box>
      </AspectRatio>
      {!isMobile && <StationMetadata {...station} />}
      <Center mt={3}>
        <Text fontSize="xl" fontWeight="500" noOfLines={1}>
          {station.title}
        </Text>
      </Center>
    </Box>
  );
};


export default function StationList({station_group, stations}: {station_group: StationGroup, stations: Station[]}) {
  return (
    <Center>
      <Grid w='91%' mt={1} templateColumns={{base: 'repeat(2, 1fr)', md: 'repeat(4, 1fr)', lg: 'repeat(5, 1fr)', xl: 'repeat(5, 1fr)'}} gap={9} >
        {Object.values(stations).length > 0 ? Object.values(stations).map((station: Station): any => (
          <GridItem as='button' key={station.id}>
            <Link href={`/${encodeURIComponent(station_group?.slug)}/${encodeURIComponent(station.slug)}`} scroll={false} passHref>
              <a><StationItem {...station} /></a>
            </Link>
          </GridItem>
        )): <GridItem as='div' colSpan={5}>
          <Text w={'100%'}>Nu există nici o stație în această categorie.</Text>
        </GridItem>}
      </Grid>
    </Center>
  );
}
