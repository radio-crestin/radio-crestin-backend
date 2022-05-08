import {NextApiRequest, NextApiResponse} from "next";
import {ListeningEvent} from "../../../types";
import { v4 as uuidv4 } from 'uuid';
import {trackListen} from "../../../backendServices/listen";

export default async function handler(req: NextApiRequest & {session: any}, res: NextApiResponse<{ done: boolean }>) {
  // TODO: the session might not work well here..
  if(typeof req.session === "undefined" || typeof req.session.ip === "undefined" || typeof req.session.id === "undefined") {
    Object.defineProperty(req, 'session', {
      value: {
        ip: (req.headers['x-forwarded-for'] as string)?.split(',')[0]?.trim() || req.socket.remoteAddress || '',
        id: uuidv4()
      },
      writable: true
    });
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
