import axios, {AxiosRequestConfig} from 'axios';
import {Review} from '../types';
import {PROJECT_ENV} from '@/utils/env';

export const postReview = (review: Review): Promise<{done: boolean}> => {
  const options: AxiosRequestConfig = {
    method: 'POST',
    url: PROJECT_ENV.FRONTEND_GRAPHQL_INTERNAL_ENDPOINT_URI,
    headers: {
      'content-type': 'application/json',
      'x-hasura-admin-secret':
        PROJECT_ENV.FRONTEND_GRAPHQL_INTERNAL_ENDPOINT_ADMIN_SECRET,
    },
    data: {
      operationName: 'InsertStationReview',
      query: `mutation InsertStationReview(
  $user_name: String
  $ip_address: String!
  $session_id: String!
  $station_id: Int!
  $stars: Int!
  $message: String
) {
  insert_reviews_one(
    object: {
      message: $message
      stars: $stars
      user: {
        data: {
          ip_address: $ip_address
          name: $user_name
          session_id: $session_id
        }
        on_conflict: {
          constraint: users_session_id_key
          update_columns: [ip_address, name]
        }
      }
      station_id: $station_id
    }
    on_conflict: {
      constraint: reviews_station_id_user_id_key
      update_columns: [message, stars]
    }
  ) {
    id
  }
}
    `,
      variables: review,
    },
  };

  return axios.request(options).then(function (response) {
    if (!response.data?.data) {
      throw new Error(`Invalid response: ${JSON.stringify(response.data)}`);
    }

    return {
      done: typeof response.data.data.insert_reviews_one.id !== 'undefined',
    };
  });
};
