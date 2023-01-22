import {NextApiRequest, NextApiResponse} from "next";
import {getAllUrls} from "../../sitemap.xml";
import {Promise} from "bluebird";
import axios from "axios";

export default async function handler(req: NextApiRequest, res: NextApiResponse<{ done: boolean, duration: number, error?: string }>) {
  console.error("process.env.refreshCacheToken", process.env.refreshCacheToken)
  if (process.env.refreshCacheToken === "" || req.query.token !== process.env.refreshCacheToken) {
    res.status(401).json({done: false, duration: 0, error: "Not authorized"});
    return;
  }
  const start = performance.now();
  getAllUrls().then(urls => {
    return Promise.map(urls, function (url: string) {
      console.log("Refreshing cache for " + url);
      return axios({
        url,
        method: 'get',
        headers: {
          'User-Agent': 'NextJs-RefreshCache',
        }
      });
    }, {concurrency: 50})
  }).then(function () {
    res.status(200).json({
      done: true,
      duration: Math.round(performance.now() - start)
    })
  }).catch(error => {
    console.error(error);
    res.status(500).json({
      done: false,
      duration: Math.round(performance.now() - start),
      error: "Unknown error"
    })
  });
}
