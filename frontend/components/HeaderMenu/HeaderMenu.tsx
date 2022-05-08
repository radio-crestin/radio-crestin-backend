
import {
  Box,
  Button,
  Flex,
  Link,
  SimpleGrid,
  Spacer,
  Tooltip
} from '@chakra-ui/react'

import styles from "./Footer.module.scss";
import {ContactModalLink} from "@/components/ContactModalLink/ContactModalLink";
import React from "react";
import InstallAppButton from "@/components/InstallAppButton/InstallAppButton";
import InviteButton from "@/components/InviteButton/InviteButton";
import RandomStationButton
  from "@/components/RandomStationButton/RandomStationButton";

export default function HeaderMenu({pickARandomStation}: any) {
  return (
    <>
      <SimpleGrid columns={{base: 1, sm: 2}} mx={{base: -1, lg: 4}} my={{base: 3, lg: 5}} h={'fit-content'} alignItems={'center'} >
        <Flex justifyContent={{base: 'center', sm: 'left'}}>
          <Box>
            <ContactModalLink/>
          </Box>
          <Box ml={{base: 2, lg: 4}}>
            <Link key="github" href="https://github.com/iosifnicolae2/radio-crestin.com" isExternal>
              Github
            </Link>
          </Box>
          <Box ml={{base: 2, lg: 4}}>
            <Link key="api" href="https://graphql-viewer.radio-crestin.com/?endpoint=cc_BYFxAcGcC4HpYOYCcCG5gEcA2A6VATASwHsBaAYyQFNIRCA7Hc4gW1gDcBGRVdbIA&query=cc_I4VwpgTgngBA4mALgZUQQ0QSwPYDsDOMA3jPulnoSZgCYzYQ2QxaIA2YMA7mAEb6ZEnMAFs0mNqUQQwaEQH0QESQAcI2AB5R5ZGXMXKYACzb4d02QqWTERkCN65xbA5IhoaOeQGMZZTLjybJhkYLiQhEz4vpgqFLgwUTFxOIFo3vHyrByJYNEQsZnBuADWMABmsohKYEEYeYjyKthkMM1k+AAUwSKCAFwwAIwANPSMkPK8UANEKiC8wfhGYDQDSQC+AJTEMLQsgjlJBSl4MMVlcwshy3TrMCApIpzUZg9n9bje2iKEWE9kchUMDuuGwXCabDQUACAHMdns-g1AWcQkJwhBCPg8HDqHQnE8WHYHE4JK4YGgIFhWriYPjOLZ7I5nGS7qyYDIAG6YMBcKi7OgAjEwf74NAwzhsgGZGHqB58vZ0sZMCBSDCpLLYcxqvDyGXYOU7KXqvYMZXA83rIA&variables=cc_N4XyA&token=public" isExternal>
              API
            </Link>
          </Box>
        </Flex>
        <Flex  mt={{base: 2, sm: 0}} justifyContent={{base: 'center', sm: 'right'}}>
          <Box ml={2}>
            <Tooltip label='Selectează o stație aleatorie' p={2}>
              <Box>
                <RandomStationButton pickARandomStation={pickARandomStation}/>
              </Box>
            </Tooltip>
          </Box>
          <Box mx={3}>
            <Tooltip label='Invită un prieten' p={2}>
              <Box>
                <InviteButton />
              </Box>
            </Tooltip>
          </Box>
          <Box mr={{base: 0, lg: 2}}>
            <Tooltip label='Adaugă comandă rapidă pe ecran' p={2}>
              <Box>
                <InstallAppButton/>
              </Box>
            </Tooltip>
          </Box>
        </Flex>
      </SimpleGrid>
    </>
  );
}
