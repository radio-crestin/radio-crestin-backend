import React from "react";
import { Station } from "types";
import {CONSTANTS} from "../../lib/constants";
import {Box, Center, Grid, GridItem, Image, Text} from "@chakra-ui/react";

const StationItem = (station: Station) => {
  return (
    <Box>
      <Image
        src={station.thumbnail_url || CONSTANTS.DEFAULT_COVER}
        alt={station.title}
        htmlHeight={250}
        htmlWidth={250}
        borderRadius={{base: '20px', lg: '41px'}}
        style={{
          "background":"linear-gradient(180.37deg, rgba(0, 0, 0, 0) 11.16%, rgba(0, 0, 0, 0.7138) 91.38%)",
          "filter": station?.uptime?.is_up ? "drop-shadow(2px 2px 5px rgba(0, 0, 0, 0.25))": "saturate(0%)",
      }}
        loading={"lazy"}
      />
      <Center mt={1}>
        <Text fontSize='lg' fontWeight='500'>{station.title}</Text>
      </Center>
    </Box>
  );
};

interface IProps {
  stations: Array<Station>;
  onStationSelect: (station: Station) => void;
}

export default function StationList(props: IProps) {
  const { stations } = props;
  return (
    <Grid w='100%' templateColumns={{base: 'repeat(2, 1fr)', md: 'repeat(4, 1fr)', lg: 'repeat(5, 1fr)', xl: 'repeat(6, 1fr)'}} gap={9} >
      {Object.values(stations).map((station: Station): any => (
        <GridItem as='button' key={station.id} onClick={() => props.onStationSelect(station)} style={{"cursor": "pointer"}}>
          <StationItem {...station} />
        </GridItem>
      ))}
    </Grid>
  );
}
