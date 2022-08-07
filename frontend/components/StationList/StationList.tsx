import React from "react";
import {Station, StationGroup} from "types";
import {CONSTANTS} from "../../lib/constants";
import {
  AspectRatio,
  Box,
  Center,
  Grid,
  GridItem,
  Image,
  Text
} from "@chakra-ui/react";
import Link from "next/link";
import {cdnImageLoader} from "../../utils/cdnImageLoader";

const StationItem = (station: Station) => {
  return (
    <Box position={'relative'} role="group">
      <AspectRatio
        position={'relative'}
        ratio={1}
      >
        <Box
          borderRadius={{base: '20px', lg: '41px'}}>
          <Image
            src={cdnImageLoader({
              src: station.now_playing?.song?.thumbnail_url || station.thumbnail_url || CONSTANTS.DEFAULT_COVER,
              width: 384,
              quality: 80
            })}
            alt={station.title + " - " + station.now_playing?.song?.name + " de " + station.now_playing?.song?.artist.name}
            boxSize='100%'
            objectFit='cover'
            htmlHeight={250}
            htmlWidth={250}
            style={{
               "filter": station?.uptime?.is_up ? "": "grayscale(1)"
            }}
          />
        </Box>
      </AspectRatio>
      {station.now_playing?.song?.name&&<Text
        as={'h4'}
        position={'absolute'}
        bottom={'110px'}
        py={1}
        px={1}
        fontSize='md'
        // mx={3}
        color={'white'}
        align={'left'}
        fontWeight={'600'}
        noOfLines={1}
        background={'black'}
        opacity={0}
        transition={'opacity .2s linear'}
        _groupHover={{ opacity: 1 }}
      >{station.now_playing?.song?.name}</Text>}
      {station.now_playing?.song?.artist.name && <Text
        as={'h5'}
        position={'absolute'}
        bottom={'87px'}
        py={0}
        px={1}
        fontSize='0.73rem'
        // mx={3}
        color={'white'}
        align={'left'}
        fontWeight={'400'}
        noOfLines={1}
        background={'black'}
        opacity={0}
        transition={'opacity .2s linear'}
        _groupHover={{ opacity: 1 }}
      >{station.now_playing?.song?.artist.name}</Text>}
      {!station.now_playing?.song?.name && !station.now_playing?.song?.artist.name && <Text
        as={'h5'}
        position={'absolute'}
        bottom={'87px'}
        py={0}
        px={1}
        fontSize='0.73rem'
        // mx={3}
        color={'white'}
        align={'left'}
        fontWeight={'400'}
        noOfLines={1}
        background={'black'}
        opacity={0}
        transition={'opacity .2s linear'}
        _groupHover={{ opacity: 1 }}
      >Metadate indisponibile</Text>}
      <Center mt={3}>
        <Text fontSize='xl'
              fontWeight='500'
              // height={55}
              noOfLines={1}>{station.title}</Text>
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
