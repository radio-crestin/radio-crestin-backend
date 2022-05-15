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
    <Box position={'relative'}>
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
          { station.now_playing?.song?.name && <Box
            position={'absolute'}
            h={'100%'}
            w={'100%'}
            bgGradient={"linear-gradient(180.37deg, rgb(255 255 255 / 0%) 11.16%, rgb(19 19 19 / 60%) 116.38%)"}/>}
        </Box>
      </AspectRatio>
      <Text
        as={'h4'}
        position={'absolute'}
        bottom={'100px'}
        fontSize='md'
        px={3}
        color={'white'}
        align={'left'}
        fontWeight={'600'}
        noOfLines={1}
      >{station.now_playing?.song?.name}</Text>
      <Text
        as={'h5'}
        position={'absolute'}
        bottom={'85px'}
        fontSize='0.73rem'
        px={3}
        color={'white'}
        align={'left'}
        fontWeight={'400'}
        noOfLines={1}
      >{station.now_playing?.song?.artist.name}</Text>
      <Center mt={1}>
        <Text fontSize='lg' fontWeight='500' height={55}>{station.title}</Text>
      </Center>
    </Box>
  );
};


export default function StationList({station_group, stations}: {station_group: StationGroup, stations: Station[]}) {
  return (
    <Grid w='100%' templateColumns={{base: 'repeat(2, 1fr)', md: 'repeat(4, 1fr)', lg: 'repeat(5, 1fr)', xl: 'repeat(6, 1fr)'}} gap={9} >
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
  );
}
