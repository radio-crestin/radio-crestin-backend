import React from 'react';
import {useRouter} from 'next/router';
import {
  Box,
  Heading,
  Link,
  List,
  ListItem,
  useToast,
  Text,
  Container,
} from '@chakra-ui/react';
import {SeoMetadata, Topic} from '../types';
import {getTopicsMetadata} from '../backendServices/topics';
import {ExternalLinkIcon} from '@chakra-ui/icons';
import HeadContainer from '@/components/HeadContainer';
import Body from '@/components/Body/Body';
import {seoStation} from '@/utils/seo';

export default function Verses({topics}: {topics: Topic[]; fullURL: string}) {
  return (
    <>
      <Body>
        <Container maxW={'8xl'}>
          <Box>
            <Heading mb={10} mt={16}>
              Versete dupa topic
            </Heading>
            <List spacing={3}>
              {topics.map(topic => (
                <ListItem key={topic.topic_slug} my={1}>
                  <Link href={`/versete/${topic.topic_slug}`} fontSize="lg">
                    {topic.topic}
                    <ExternalLinkIcon mx="2px" />
                  </Link>
                </ListItem>
              ))}
            </List>
          </Box>
        </Container>
      </Body>
    </>
  );
}

export async function getServerSideProps(context: any) {
  const {req, res} = context;
  res.setHeader(
    'Cache-Control',
    'public, s-maxage=10, stale-while-revalidate=59',
  );
  const host = req.headers.host;
  const topics = (await getTopicsMetadata()).topics;
  return {
    props: {
      topics,
      fullURL: `https://www.${host}`,
    },
  };
}
