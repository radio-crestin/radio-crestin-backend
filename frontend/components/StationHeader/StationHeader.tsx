import React, { useEffect, useState } from "react";

import InviteButton from "@/components/InviteButton/InviteButton";
import RandomStationButton from "@/components/RandomStationButton/RandomStationButton";
import StationInformation from "@/components/StationInformation/StationInformation";
import dynamic from "next/dynamic";
import { Station } from "../../types";
import {
  Box,
  Flex,
  Spacer
} from "@chakra-ui/react";

export const StationPlayer = dynamic(
  () => import("components/StationPlayer/StationPlayer"),
  {
    ssr: true,
  },
);

export default function StationHeader(station: Station) {
  const [showChild, setShowChild] = useState(false);

  useEffect(() => {
    setShowChild(true);
  }, []);

  if (!showChild) {
    return null;
  }

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
        <RandomStationButton />
      </Flex>
      <Flex mt={{base: 1, lg: 12}} mb={2}>
        <StationPlayer
          key={station?.id}
          station={station}
        />
        <Box w={{base: '100%', lg: '74%'}} minW={{base: 'auto', lg: '400px'}}  pl={{base: 1, lg: 4}}>
          <StationInformation station={station} />
        </Box>
      </Flex>
    </Flex>
  );
}
