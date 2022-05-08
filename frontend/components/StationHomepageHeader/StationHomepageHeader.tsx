import React, { useEffect, useState } from "react";

import InviteButton from "@/components/InviteButton/InviteButton";
import RandomStationButton from "@/components/RandomStationButton/RandomStationButton";
import StationInformation from "@/components/StationInformation/StationInformation";
import {
  Box,
  Flex,
  Spacer
} from "@chakra-ui/react";
import StationPlayer from "@/components/StationPlayer/StationPlayer";
import {Station} from "../../types";


export default function StationHomepageHeader({selectedStation, pickARandomStation}: { selectedStation: Station, pickARandomStation: any }) {
  return (
    <Flex
      mt={4}
      mb={4}
      px={{base: 4, lg:14}}
      pt={{base: 4, lg:10}}
      pb={{base: 6, lg:12}}
      bg={'brand.600'}
      flexDirection={'column'}
    >
      <Flex w='100%'>
        <InviteButton />
        <Spacer />
        <RandomStationButton pickARandomStation={pickARandomStation}/>
      </Flex>
      <Flex mt={{base: 1, lg: 12}} mb={2}>
        <StationPlayer
          key={selectedStation?.id}
          station={selectedStation}
        />
        <Box w={{base: '100%', lg: '74%'}} minW={{base: 'auto', lg: '400px'}}  pl={{base: 1, lg: 4}}>
          <StationInformation station={selectedStation} />
        </Box>
      </Flex>
    </Flex>
  );
}
