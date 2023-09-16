import {Box, Flex, Link, SimpleGrid} from '@chakra-ui/react';

import React from 'react';

export default function Footer() {
  return (
    <>
      <SimpleGrid columns={{base: 1}} h={'fit-content'} alignItems={'left'}>
        <Flex justifyContent={{base: 'center', sm: 'left'}}>
          <Box>
            <Link
              key="github"
              href="https://github.com/iosifnicolae2/radio-crestin.com"
              isExternal>
              Github
            </Link>
          </Box>
          <Box ml={{base: 4, lg: 6}} mb={24}>
            <Link
              key="api"
              href="https://graphql-viewer.radio-crestin.com/?endpoint=cc_BYFxAcGcC4HpYOYCcCG5gEcA2A6VATASwHsBaAYyQFNIRCA7Hc4gW1gDcBGRVdbIA&query=cc_I4VwpgTgngBA4mALgZUQQ0QSwPYDsDOMA3jPulnoSZgCYzYQ2QxaIA2YMA7mAEb6ZEnMAFs0mNqUQQwaEQH0QESQAcI2AB5R5ZGXMXKYACzb4d02QqWTERkCN65xbAzezoXbTGTC5IhJnwAYwhMFQpcGECQsIj5NCC41g4osGDQ8JxceS9cAGsYADNZRCUwHIw0xHkVbDIYWrJ8AAovEUEALhgARgAaekZIeV4oLpIVEF4vfCMwGi7omABfAEpiGFoWQRTojIiYXIKJqe9ZuiWYEEyRTmozK4PK3CDtEUIsG7I5FWWYXGwuDU2GgoJhcABzdabD5Vb6kPCQ6h0Jw3Fh2BxOCSuGBoCBYepIv5yTi2eyOZzYi5UmAyABumDAXCoGzoXwghE++DQ4M41K+cXB6iuzM2KM4DCYECkGCy8kQ2HMMrw8kF2GF635ss2EuY1IuQA&variables=cc_N4XyA"
              isExternal>
              API
            </Link>
          </Box>
          <Box ml={{base: 4, lg: 6}} mb={24}>
            <Link key="privacy-policy" href="/privacy-policy" isExternal>
              Politică de confidențialitate
            </Link>
          </Box>
        </Flex>
      </SimpleGrid>
    </>
  );
}
