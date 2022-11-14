import axios, {AxiosRequestConfig} from 'axios';
import {ListeningEvent} from '../types';
import {PROJECT_ENV} from '@/utils/env';

export const trackListen = (
  listeningEvent: ListeningEvent,
): Promise<{done: boolean}> => {
  const options: AxiosRequestConfig = {
    method: 'POST',
    url: PROJECT_ENV.FRONTEND_GRAPHQL_INTERNAL_ENDPOINT_URI,
    headers: {
      'content-type': 'application/json',
      'x-hasura-admin-secret':
        PROJECT_ENV.FRONTEND_GRAPHQL_INTERNAL_ENDPOINT_ADMIN_SECRET,
    },
    data: {
      operationName: 'InsertListeningEvent',
      query: `mutation InsertListeningEvent(
  $session_id: String!
  $ip_address: String!
  $station_id: Int!
  $info: jsonb!
) {
  insert_listening_events_one(
    object: {
      user: {
        data: { session_id: $session_id, ip_address: $ip_address }
        on_conflict: {
          constraint: users_session_id_key
          update_columns: ip_address
        }
      }
      station_id: $station_id
      info: $info
    }
  ) {
    id
  }
}

    `,
      variables: listeningEvent,
    },
  };

  return axios.request(options).then(function (response) {
    if (!response.data?.data) {
      throw new Error(`Invalid response: ${JSON.stringify(response.data)}`);
    }

    return {
      done:
        typeof response.data.data.insert_listening_events_one.id !==
        'undefined',
    };
  });
};
