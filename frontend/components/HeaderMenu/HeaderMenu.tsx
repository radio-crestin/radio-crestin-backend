
import {Box, Flex, Link, SimpleGrid} from '@chakra-ui/react'

import styles from "./Footer.module.scss";
import {ContactModalLink} from "@/components/ContactModalLink/ContactModalLink";

export default function HeaderMenu() {
  return (
    <>
      <Flex mt={{base: 4, lg: 6}}>
        <Box>
          <ContactModalLink/>
        </Box>
        <Box ml={4}>
          <Link key="github" href="https://github.com/iosifnicolae2/radio-crestin.com" isExternal>
            Github
          </Link>
        </Box>
        <Box ml={4}>
          <Link key="api" href="https://graphql-viewer.radio-crestin.com/?endpoint=cc_BYFxAcGcC4HpYOYCcCG5gEcA2A6VATASwHsBaAYyQFNIRCA7Hc4gW1gDcBGRVdbIA&query=cc_I4VwpgTgngBA4mALgZUQQ0QSwPYDsDOMA3jPulnoSZgCYzYQ2QxaIA2YMA7mAEb6ZEnMAFs0mNqUQQwaEQH0QESQAcI2AB5R5ZGXMXKYACzb4d02QqWTERkCN65xbA5IhoaOeQGMZZTLjybJhkYLiQhEz4vpgqFLgwUTFxOIFo3vHyrByJYNEQsZnBuADWMABmsohKYEEYeYjyKthkMM1k+AAUwSKCAFwwAIwANPSMkPK8UANEKiC8wfhGYDQDSQC+AJTEMLQsgjlJBSl4MMVlcwshy3TrMCApIpzUZg9n9bje2iKEWE9kchUMDuuGwXCabDQUACAHMdns-g1AWcQkJwhBCPg8HDqHQnE8WHYHE4JK4YGgIFhWriYPjOLZ7I5nGS7qyYDIAG6YMBcKi7OgAjEwf74NAwzhsgGZGHqB58vZ0sZMCBSDCpLLYcxqvDyGXYOU7KXqvYMZXA83rIA&variables=cc_N4XyA&token=public" isExternal>
            API
          </Link>
        </Box>
      </Flex>
    </>
  );
}
