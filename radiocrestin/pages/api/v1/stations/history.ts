const glob = require("glob");
import absoluteUrl from 'next-absolute-url'
import {HISTORY_DATA_DIRECTORY_PATH} from '../../../../constants';


export default async function handler(req: any, res: any) {
  const {origin} = absoluteUrl(req)
  const history = glob.sync(`${HISTORY_DATA_DIRECTORY_PATH}/*/*.json`).map((f: string) => {
    return `${origin}/${f.replace("./public/", "")}`;
  }).reverse();
  res.status(200).json({history})
}
