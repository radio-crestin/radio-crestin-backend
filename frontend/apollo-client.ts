import {ApolloClient, DefaultOptions, InMemoryCache} from '@apollo/client';
import {PROJECT_ENV} from '@/utils/env';

const defaultOptions: DefaultOptions = {
  watchQuery: {
    fetchPolicy: 'cache-and-network',
    errorPolicy: 'all',
    pollInterval: 5000,
  },
};

const client = new ApolloClient({
  uri: PROJECT_ENV.FRONTEND_GRAPHQL_INTERNAL_ENDPOINT_URI,
  cache: new InMemoryCache(),
  defaultOptions: defaultOptions,
});

export default client;
