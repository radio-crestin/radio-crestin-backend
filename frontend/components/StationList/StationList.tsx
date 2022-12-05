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
  Text,
} from '@chakra-ui/react';
import Link from 'next/link';
import { ImageWithFallback } from '../ImageWithFallback/ImageWithFallback';

const StationMetadata = dynamic(
  () => import('@/components/StationMetadata/StationMetadata'),
  {ssr: false},
);

const StationItem = ({station, priority}: {station: Station, priority: boolean}) => {
  return (
    <Box position={'relative'} role="group">
      <AspectRatio position={'relative'} ratio={1}>
        <Box borderRadius={{base: '20px', lg: '41px'}}
             position={'relative'}
             width={250}
             height={250}
             overflow={'hidden'}>

            <ImageWithFallback
              src={station.now_playing?.song?.thumbnail_url ||
                station.thumbnail_url ||
                CONSTANTS.DEFAULT_COVER}
              fallbackSrc={station.thumbnail_url || CONSTANTS.DEFAULT_COVER}
              alt={station.title}
              priority={priority}
              fill
              sizes="250px"
              style={{
                filter: station?.uptime?.is_up ? '' : 'grayscale(1)',
                objectFit: "cover",
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

export default function StationList({
  station_group,
  stations,
}: {
  station_group: StationGroup;
  stations: Station[];
}) {
  return (
    <Center>
      <Grid
        w="91%"
        mt={1}
        templateColumns={{
          base: 'repeat(2, 1fr)',
          md: 'repeat(4, 1fr)',
          lg: 'repeat(5, 1fr)',
          xl: 'repeat(5, 1fr)',
        }}
        gap={9}>
        {Object.values(stations).length > 0 ? (
          Object.values(stations).map((station: Station, index): any => (
            <GridItem as="button" key={station.id}>
              <Link
                prefetch={false}
                href={`/${encodeURIComponent(
                  station_group?.slug,
                )}/${encodeURIComponent(station.slug)}`}
                scroll={false}
                passHref>
                <StationItem station={station} priority={index < 6}/>
              </Link>
            </GridItem>
          ))
        ) : (
          <GridItem as="div" colSpan={5}>
            <Text w={'100%'}>
              Nu există nici o stație în această categorie.
            </Text>
          </GridItem>
        )}
      </Grid>
    </Center>
  );
}
