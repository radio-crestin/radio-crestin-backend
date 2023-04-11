import {StationsMetadata, TopicsMetadata} from '../types';
import {PROJECT_ENV} from '@/utils/env';

const cachios = require('cachios');

export const getTopicsMetadata = (): Promise<TopicsMetadata> => {
  return cachios
    .post(
      PROJECT_ENV.FRONTEND_GRAPHQL_BIBLE_INTERNAL_ENDPOINT_URI,
      {
        operationName: 'getTopics',
        query: `
query getTopics {
  bible_topic_aggregate(distinct_on: topic, order_by: {topic: asc}) {
    nodes {
      topic
      topic_slug
    }
  }
}


    `,
        variables: {},
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

      return {
        topics: response.data.data.bible_topic_aggregate.nodes,
      };
    });
};
