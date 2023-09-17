import client from '../apollo-client';
import {getStationsQuery} from '../graphql/queries';

const cachios = require('cachios');

export const getStations = async () => {
  const {data} = await client.query({
    query: getStationsQuery,
  });

  return data;
};
