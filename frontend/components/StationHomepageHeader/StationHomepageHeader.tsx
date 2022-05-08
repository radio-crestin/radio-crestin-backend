import React from "react";

import StationInformation from "@/components/StationInformation/StationInformation";
import {
  Box,
  Flex,
} from "@chakra-ui/react";
import StationPlayer from "@/components/StationPlayer/StationPlayer";
import {Station} from "../../types";


export default function StationHomepageHeader({selectedStation}: { selectedStation: Station }) {
  return (
    <Flex
      mx={{base: -4, lg: 0}}
      px={{base: 3, lg: 12}}
      py={{base: 3, lg: 6}}
      bg={'brand.600'}
      flexDirection={'column'}
    >
      <Flex mt={{base: 1, lg: 12}} mb={2}>
        <StationPlayer
          key={selectedStation?.id}
          station={selectedStation}
        />
        <Box w={{base: '100%', lg: '71%'}} minW={{base: 'auto', lg: '400px'}}  pl={{base: 1, lg: 4}}>
          <StationInformation station={selectedStation} />
        </Box>
      </Flex>
    </Flex>
  );
}
