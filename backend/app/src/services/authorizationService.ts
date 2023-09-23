import { Request } from "express";
import axios, {AxiosRequestConfig} from "axios";
import {PROJECT_ENV} from "@/env";

export const authenticationService = (req: Request): Promise<any> => {

  console.log("request:", {
    cookies: req.cookies,
    headers: req.headers,
    body: req.body,
    query: req.query,
  });

  return new Promise((resolve) => {
    resolve(true);
  }).then(async () => {
    const {user_ip, session_id} = req as any;

    if(!session_id) {
      return {
        "X-Hasura-Role": "public",
        "X-Hasura-User-Ip": user_ip,
      };
    }

    const options: AxiosRequestConfig = {
      method: "POST",
      url: PROJECT_ENV.APP_GRAPHQL_ENDPOINT_URI,
      headers: {
        "content-type": "application/json",
        "x-hasura-admin-secret": PROJECT_ENV.APP_GRAPHQL_ADMIN_SECRET,
      },
      data: {
        operationName: "UpsertUser",
        query: `mutation UpsertUser($ip_address: String!, $session_id: String!) {
  insert_users_one(object: {session_id: $session_id, ip_address: $ip_address}, on_conflict: {constraint: users_session_id_key, update_columns: ip_address}) {
    id
  }
}`,
        variables: {
          ip_address: user_ip,
          session_id: session_id,
        },
      },
    };

    const userId = await axios.request(options).then(function (response) {
      if (!response.data?.data) {
        throw new Error(`Invalid response: ${JSON.stringify(response.data)}`);
      }
      return response.data.data.insert_users_one.id;
    });

    return {
      "X-Hasura-Role": "user",
      "X-Hasura-User-Id": userId.toString(),
      "X-Hasura-User-Session-Id": session_id.toString(),
      "X-Hasura-User-Ip": user_ip,
    };

  });
};
