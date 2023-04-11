import {useRouter} from 'next/router';
import {useToast} from '@chakra-ui/react';
import React from 'react';
import {parse} from 'url';
import {getTopicMetadata} from '../../backendServices/topic';

export default function VersesByTopic({topic_slug, topic_metadata}: any) {
  const router = useRouter();
  const toast = useToast();

  return (
    <div>
      <h1>Versete pentru topicul: {topic_slug}</h1>
      <ul>
        {topic_metadata.map((topicM: any) => {
          const humanFriendlyBookName = topicM.verses[0]?.book || topicM.book;
          return (
            <li key={topicM.id}>
              <p>
                <strong>
                  {humanFriendlyBookName} {topicM.chapter}:{topicM.verse_from}-
                  {topicM.verse_to}
                </strong>
                {topicM.verses.map((verse: any) => (
                  <li key={verse.id}>
                    <p>
                      <strong>
                        {verse.book} {verse.chapter}:{verse.verse}
                      </strong>
                      <pre>{verse.content}</pre>
                    </p>
                  </li>
                ))}
                <br />
                <br />
                <br />
              </p>
            </li>
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
  console.log({topic_slug});
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
