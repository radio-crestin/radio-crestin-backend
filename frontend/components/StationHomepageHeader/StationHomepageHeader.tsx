import React from "react";

import StationInformation
  from "@/components/StationInformation/StationInformation";
import { Box, Flex } from "@chakra-ui/react";
import StationPlayer from "@/components/StationPlayer/StationPlayer";
import { Station } from "../../types";

export default function StationHomepageHeader({selectedStation}: { selectedStation: Station }) {
  return (
    <Flex
      borderRadius={{base: 12, lg: 40}}
      mx={{ base: -2, lg: "auto" }}
      mt={{ base: 0, lg: 5 }}
      mb={{ base: 0, lg: 12 }}
      px={{base: 3, lg: 16}}
      py={{base: 3, lg: 14}}
      bg={'brand.600'}
      flexDirection={'column'}
    >
      <Flex >
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
