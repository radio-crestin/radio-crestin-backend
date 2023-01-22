import {ClientSideReview} from "../types";

export const postReviewClientSide = (review: ClientSideReview): Promise<{ done: boolean }> => {
  return fetch(process.env.NEXT_PUBLIC_FRONTEND_API_PREFIX + '/api/v1/review', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(review)
  }).then((res) => res.json()).catch(e => {
    console.error(e);
    return {done: false}
  });
};
