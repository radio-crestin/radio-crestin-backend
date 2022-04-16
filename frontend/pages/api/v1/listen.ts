import {getSession} from "../../../lib/session";
import {NextApiRequest, NextApiResponse} from "next";
import {ListeningEvent, Review} from "../../../types";
import {postReview} from "../../../services/review";
import { v4 as uuidv4 } from 'uuid';
import {trackListen} from "../../../services/listen";

export default async function handler(req: NextApiRequest, res: NextApiResponse<{ done: boolean }>) {
  req.session.ip = req.headers['x-forwarded-for'] || req.socket.remoteAddress
  if(!req.session.id) {
    req.session.id = uuidv4();
  }
  // TODO: we might need to implement a protection mechanism here..

  const listeningEvent: ListeningEvent = {
    ip_address: req.session.ip,
    session_id: req.session.id,
    station_id: req.query.station_id || req.body.station_id,
    info: req.body.info || {},
  }
  return trackListen(listeningEvent).then(response => {
    res.status(200).json({done: response.done})
  })
}
