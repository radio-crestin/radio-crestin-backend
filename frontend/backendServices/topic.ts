import {StationsMetadata, TopicsMetadata} from '../types';
import {PROJECT_ENV} from '@/utils/env';

const cachios = require('cachios');

export const getTopicMetadata = (topic_slug: string): Promise<any> => {
  return cachios
    .post(
      PROJECT_ENV.FRONTEND_GRAPHQL_BIBLE_INTERNAL_ENDPOINT_URI,
      {
        operationName: 'getTopic',
        query: `
query getTopic($topic_slug: String!) {
  bible_topic(where: {topic_slug: {_eq: $topic_slug}}, order_by: {book: asc, chapter: asc, verse_from: asc}) {
    id
    topic
    topic_slug
    book
    chapter
    verse_from
    verse_to
    verses {
      id
      book
      chapter
      verse
      content
    }
  }
}

    `,
        variables: {
          topic_slug: topic_slug,
        },
      },
      {
        headers: {
          'content-type': 'application/json',
        },
        ttl: 5,
      },
    )
    .then(function (response: any) {
      if (!response.data?.data) {
        throw new Error(`Invalid response: ${JSON.stringify(response.data)}`);
      }

      return response.data.data.bible_topic;
    });
};
