import React from "react";
import {Station, StationGroup} from "types";
import {CONSTANTS} from "../../lib/constants";
import {Box, Center, Grid, GridItem,  Text} from "@chakra-ui/react";
import Link from "next/link";
import Image from 'next/image'
import {cdnImageLoader} from "../../utils/cdnImageLoader";

const StationItem = (station: Station) => {
  return (
    <Box>
      <Image
        src={station.thumbnail_url || CONSTANTS.DEFAULT_COVER}
        alt={station.title}
        loader={cdnImageLoader}
        width={250}
        height={250}
        // htmlHeight={250}
        // htmlWidth={250}
        // borderRadius={{base: '20px', lg: '41px'}}
        style={{
          "background":"linear-gradient(180.37deg, rgba(0, 0, 0, 0) 11.16%, rgba(0, 0, 0, 0.7138) 91.38%)",
          "filter": station?.uptime?.is_up ? "drop-shadow(2px 2px 5px rgba(0, 0, 0, 0.25))": "saturate(0%)",
      }}
        loading={"lazy"}
      />
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
