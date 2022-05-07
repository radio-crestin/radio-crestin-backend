import {NextApiRequest, NextApiResponse} from "next";
import {Review} from "../../../types";
import {postReview} from "../../../backendServices/review";
import { v4 as uuidv4 } from 'uuid';

export default async function handler(req: NextApiRequest, res: NextApiResponse<{ done: boolean }>) {
  // @ts-ignore
  if(!req.session) {
    Object.defineProperty(req, 'session', {});
  }
  // @ts-ignore
  req.session.ip = req.headers['x-forwarded-for'] || req.socket.remoteAddress
  // @ts-ignore
  if(!req.session.id) {
    // @ts-ignore
    req.session.id = uuidv4();
  }
  // TODO: we might need to implement a protection mechanism here..


  const review: Review = {
    user_name: req.query.user_name || req.body.user_name,
    // @ts-ignore
    ip_address: req.session.ip,
    // @ts-ignore
    session_id: req.session.id,
    station_id: req.query.station_id || req.body.station_id,
    stars: req.query.stars || req.body.stars,
    message: req.query.message || req.body.message,
  }
  return postReview(review).then(response => {
    res.status(200).json({done: response.done})
  })
}
