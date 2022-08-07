
import {
  Box,
  Flex,
  Link,
  SimpleGrid,
} from '@chakra-ui/react'

import React from "react";
import {ContactModalLink} from "@/components/ContactModalLink/ContactModalLink";

export default function Footer() {
  return (
    <>
      <SimpleGrid
        columns={{base: 1}}
        mt={{base: 3, lg: 20}}
        h={'fit-content'}
        alignItems={'left'}
      >
        <Flex justifyContent={{base: 'center', sm: 'left'}}>
            <Box>
              <Link key="github" href="https://github.com/iosifnicolae2/radio-crestin.com" isExternal>
                Github
              </Link>
            </Box>
            <Box ml={{base: 4, lg: 6}}>
              <Link key="api" href="https://graphql-viewer.radio-crestin.com/?endpoint=cc_BYFxAcGcC4HpYOYCcCG5gEcA2A6VATASwHsBaAYyQFNIRCA7Hc4gW1gDcBGRVdbIA&query=cc_I4VwpgTgngBA4mALgZUQQ0QSwPYDsDOMA3jPulnoSZgCYzYQ2QxaIA2YMA7mAEb6ZEnMAFs0mNqUQQwaEQH0QESQAcI2AB5R5ZGXMXKYACzb4d02QqWTERkCN65xbA5IhoaOeQGMZZTLjybJhkYLiQhEz4vpgqFLgwUTFxOIFo3vHyrByJYNEQsZnBuADWMABmsohKYEEYeYjyKthkMM1k+AAUwSKCAFwwAIwANPSMkPK8UANEKiC8wfhGYDQDSQC+AJTEMLQsgjlJBSl4MMVlcwshy3TrMCApIpzUZg9n9bje2iKEWE9kchUMDuuGwXCabDQUACAHMdns-g1AWcQkJwhBCPg8HDqHQnE8WHYHE4JK4YGgIFhWriYPjOLZ7I5nGS7qyYDIAG6YMBcKi7OgAjEwf74NAwzhsgGZGHqB58vZ0sZMCBSDCpLLYcxqvDyGXYOU7KXqvYMZXA83rIA&variables=cc_N4XyA&token=public" isExternal>
                API
              </Link>
            </Box>
            <Box ml={{base: 4, lg: 6}}>
              <ContactModalLink/>
            </Box>
          </Flex>
      </SimpleGrid>
    </>
  );
}
