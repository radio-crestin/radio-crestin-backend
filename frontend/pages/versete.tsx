import React from 'react';
import {useRouter} from 'next/router';
import {useToast} from '@chakra-ui/react';
import {Topic} from '../types';
import {getTopicsMetadata} from '../backendServices/topics';

export default function Verses({topics}: {topics: Topic[]; fullURL: string}) {
  const router = useRouter();
  const toast = useToast();

  return (
    <div>
      <h1>Versete dupa topic</h1>
      <ul>
        {topics.map(topic => (
          <li key={topic.topic_slug}>
            <a href={`/versete/${topic.topic_slug}`}>{topic.topic}</a>
          </li>
        ))}
      </ul>
    </div>
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
