import {NextApiRequest, NextApiResponse} from "next";
import {ListeningEvent} from "../../../types";
import { v4 as uuidv4 } from 'uuid';
import {trackListen} from "../../../backendServices/listen";

export default async function handler(req: NextApiRequest, res: NextApiResponse<{ done: boolean }>) {
  // @ts-ignore
  req.session.ip = req.headers['x-forwarded-for'] || req.socket.remoteAddress || '';
  // @ts-ignore
  console.log("ip: ", req?.session?.ip, req.headers, req.socket.remoteAddress)
  // @ts-ignore
  if(!req.session.id) {
    // @ts-ignore
    req.session.id = uuidv4();
  }
  // TODO: we might need to implement a protection mechanism here..

  const listeningEvent: ListeningEvent = {
    // @ts-ignore
    ip_address: req.session.ip,
    // @ts-ignore
    session_id: req.session.id,
    station_id: req.query.station_id || req.body.station_id,
    info: req.body.info || {},
  }
  return trackListen(listeningEvent).then(response => {
    res.status(200).json({done: response.done})
  })
}
