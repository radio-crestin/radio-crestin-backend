import React from 'react';
import dynamic from 'next/dynamic';
import Link from 'next/link';

import {Station, StationGroup} from 'types';
import {CONSTANTS} from '../../lib/constants';
import {
  AspectRatio,
  Box,
  Center,
  Grid,
  GridItem,
  Text,
  useMediaQuery,
} from '@chakra-ui/react';
import {ImageWithFallback} from '../ImageWithFallback/ImageWithFallback';
import {ViewIcon} from '@chakra-ui/icons';
import {useRouter} from 'next/router';

const StationMetadata = dynamic(
  () => import('@/components/StationMetadata/StationMetadata'),
  {ssr: false},
);

const StationItem = ({
  station,
  is_listening,
}: {
  station: Station;
  is_listening?: boolean;
}) => {
  // TODO: calculate this on the backend
  const metadataUpToDate = station?.now_playing?.timestamp
    ? new Date().getTime() - new Date(station.now_playing.timestamp).getTime() <
      1000 * 60 // 60 seconds
    : false;

  const numberOfListeners = station?.total_listeners
    ? station?.total_listeners + (is_listening ? 1 : 0)
    : null;
  const [isTabletOrMobile] = useMediaQuery('(max-width: 1024px)');
  return (
    <Box position={'relative'} role="group">
      <AspectRatio position={'relative'} ratio={1}>
        <Box
          borderRadius={{base: '20px', lg: '41px'}}
          position={'relative'}
          overflow={'hidden'}
          height={250}
          width={250}>
          {metadataUpToDate && numberOfListeners && (
            <Text
              position={'absolute'}
              display={'flex'}
              justifyContent={'center'}
              alignItems={'center'}
              background={'rgba(0,0,0,0.68)'}
              color={'white'}
              paddingX={1}
              borderRadius={10}
              right={4}
              top={3}
              fontSize={14}
              gap={1}>
              <ViewIcon />
              {numberOfListeners}
            </Text>
          )}
          <ImageWithFallback
            src={
              station.now_playing?.song?.thumbnail_url ||
              station.thumbnail_url ||
              CONSTANTS.DEFAULT_COVER
            }
            fallbackSrc={station.thumbnail_url || CONSTANTS.DEFAULT_COVER}
            alt={`${station.title} | Radio Crestin`}
            style={{
              filter: station?.uptime?.is_up ? 'unset' : 'grayscale(1)',
              objectFit: 'cover',
              width: '100%',
              height: '100%',
            }}
          />
          {metadataUpToDate && !station?.uptime?.is_up && (
            <Box
              position={'absolute'}
              bottom={0}
              width={'100%'}
              height={6}
              display={'flex'}
              justifyContent={'end'}
              alignItems={'center'}
              color={'white'}>
              <Text
                as={'p'}
                bg={'#d52619'}
                py={'1px'}
                px={'6px'}
                borderRadius={30}
                position={'relative'}
                right={'7%'}
                bottom={'10px'}
                fontSize={'0.7rem'}
                fontWeight={'400'}>
                offline
              </Text>
            </Box>
          )}
        </Box>
      </AspectRatio>
      {metadataUpToDate && !isTabletOrMobile && (
        <StationMetadata {...station} />
      )}
      <Center mt={3}>
        <Text fontSize="sm" fontWeight="300" noOfLines={1} mt={'-3px'}>
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
  const route = useRouter();
  // @ts-ignore
  const selectedStation: Station = stations.find(
    s => s.slug === route.asPath.split('/')[2],
  );

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
          Object.values(stations).map((station: Station): any => (
            <GridItem as="button" key={station.id}>
              <Link
                prefetch={false}
                href={`/${encodeURIComponent(
                  station_group?.slug,
                )}/${encodeURIComponent(station.slug)}`}
                scroll={false}
                passHref>
                <StationItem
                  station={station}
                  is_listening={station === selectedStation || false}
                />
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
