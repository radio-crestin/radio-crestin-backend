import {useRouter} from 'next/router';
import {Box, Heading, List, ListItem, useToast} from '@chakra-ui/react';
import React from 'react';
import {parse} from 'url';
import {getTopicMetadata} from '../../backendServices/topic';

export default function VersesByTopic({topic_slug, topic_metadata}: any) {
  return (
    <div>
      <h1>Versete pentru topicul: {topic_slug}</h1>
      <ul>
        {topic_metadata.map((topicM: any) => {
          const humanFriendlyBookName = topicM.verses[0]?.book || topicM.book;
          return (
            <Box key={topicM.id}>
              <Heading>
                {humanFriendlyBookName} {topicM.chapter}:{topicM.verse_from}-
                {topicM.verse_to}
              </Heading>
              <List key={topicM.id + '-verses'}>
                {topicM.verses.map((verse: any) => (
                  <ListItem key={topicM.id + '-' + verse.id}>
                    <strong>
                      {verse.book} {verse.chapter}:{verse.verse}
                    </strong>
                    <pre>{verse.content}</pre>
                  </ListItem>
                ))}
              </List>
              <br />
              <br />
              <br />
            </Box>
          );
        })}
      </ul>
    </div>
  );
}

export async function getServerSideProps(context: any) {
  const {req, res, query} = context;
  res.setHeader(
    'Cache-Control',
    'public, s-maxage=10, stale-while-revalidate=59',
  );
  const {topic_slug} = query;
  const topic_metadata = await getTopicMetadata(topic_slug);
  const {pathname} = parse(req.url, true);
  const host = req.headers.host;

  return {
    props: {
      topic_metadata,
      topic_slug,
      fullURL: `https://www.${host}${pathname}`,
    },
  };
}
