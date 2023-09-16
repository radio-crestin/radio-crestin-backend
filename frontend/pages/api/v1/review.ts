import {NextApiRequest, NextApiResponse} from "next";
import {Review} from "../../../types";
import {postReview} from "../../../backendServices/review";
import { v4 as uuidv4 } from 'uuid';

export default async function handler(
  req: NextApiRequest & {session: any},
  res: NextApiResponse<{done: boolean}>,
) {
  if (
    typeof req.session === 'undefined' ||
    typeof req.session.ip === 'undefined' ||
    typeof req.session.id === 'undefined'
  ) {
    Object.defineProperty(req, 'session', {
      value: {
        ip:
          (req.headers['x-forwarded-for'] as string)?.split(',')[0]?.trim() ||
          req.socket.remoteAddress ||
          '',
        id: uuidv4(),
      },
      writable: true,
    });
  }
  // TODO: we might need to implement a protection mechanism here..

  const review: Review = {
    user_name: req.query.user_name || req.body.user_name,
    ip_address: req.session.ip,
    session_id: req.session.id,
    station_id: req.query.station_id || req.body.station_id,
    stars: req.query.stars || req.body.stars,
    message: req.query.message || req.body.message,
  };
  return postReview(review)
    .then(response => {
      res.status(200).json({done: response.done});
    })
    .catch(error => {
      console.error('error', error);
      res.status(500).json({done: false});
    });
}
