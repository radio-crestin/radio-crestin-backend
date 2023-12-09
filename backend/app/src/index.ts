import express, { NextFunction, Request, Response } from "express";
import { refreshStationsMetadata } from "./services/stationScrape";
import { Logger } from "tslog";
import { PROJECT_ENV } from "./env";
import * as cron from "node-cron";
import { refreshStationsRssFeed } from "./services/stationRssFeedScrape";
import axios from "axios";
import {authorizationService} from "./services/authorizationService";
import cookieParser from "cookie-parser";

const app = express();

const port = PROJECT_ENV.APP_SERVER_PORT;

const logger: Logger<any> = new Logger({ name: "index", minLevel: PROJECT_ENV.APP_DEBUG? 2: 3 });

// Axios config
axios.defaults.timeout = 10 * 1000;

// This might consume a lot of memory if axios has to buffer a lot of requests
// axiosThrottle.use(axios, { requestsPerSecond: 60 });

// TODO: this might introduce a memory leak..
// TODO: also, we might need to disable this for local requests..
// axios.interceptors.response.use(
//   (response) => {
//     return response;
//   },
//   async (error) => {
//     error.config.count = (error?.config?.count || 0) + 1;
//     logger.info("MYERROR:", {error_config: error.config});
//
//     if (
//       (!error?.response?.status || error.response.status !== 200) &&
//       error.config.count < 4
//     ) {
//       if (error.config.count % 2 === 1 && PROJECT_ENV.SOCKS5_RETRY_PROXY) {
//         logger.info("retrying the request using the SOCKS5_RETRY_PROXY");
//
//         const agent = new SocksProxyAgent(
//           `socks5://${randomUUID()}:test@${PROJECT_ENV.SOCKS5_RETRY_PROXY}`
//         );
//         return axios.request({
//           ...error.config,
//           ...{
//             httpAgent: agent,
//             httpsAgent: agent,
//           },
//         });
//       } else {
//         await new Promise((resolve) => {
//           logger.info("waiting 500ms before retrying");
//           setTimeout(() => resolve(true), 500);
//         });
//         return await axios.request({
//           ...error.config,
//         });
//       }
//     }
//     return Promise.reject(error);
//   }
// );

app.use(cookieParser() as any);

app.use((req, res, next) => {
  (req as any).user_ip = (req.headers["x-forwarded-for"] as string)?.split(",")[0]?.trim() || req.socket.remoteAddress || "";

  // TODO: in the future, we might use a signed session id here, for now it's ok like this
  (req as any).session_id = (
    req.cookies["Session-Id"]
      || req.headers["session-id"]
      || req.body?.session_id
      || req.query?.session_id
      || req.cookies["Device-Id"]
      || req.headers["device-id"]
  );

  next();
});

app.get(
  "/",
  async (request: Request, response: Response, next: NextFunction) => {
    response.status(200).json({ up: true });
  }
);

app.use(
  "/api/v1/webhook/authentication",
  async (request: Request, response: Response, next: NextFunction) => {
    authorizationService(request)
      .then((r) => {
        response.status(200).json(r);
      })
      .catch((error) => {
        logger.error(error.toString());
        response.status(500).json({ error });
      });
  }
);

app.get(
  "/refreshStationsMetadata",
  (request: Request, response: Response, next: NextFunction) => {
    refreshStationsMetadata()
      .then((result) => {
        response.status(200).json({ result });
      })
      .catch((error) => {
        logger.error(error.toString());
        response.status(500).json({ error });
      });
  }
);

app.get(
  "/refreshStationsRssFeed",
  (request: Request, response: Response, next: NextFunction) => {
    refreshStationsRssFeed()
      .then((result) => {
        response.status(200).json({ result });
      })
      .catch((error) => {
        logger.error(error.toString());
        response.status(500).json({ error });
      });
  }
);

if (PROJECT_ENV.APP_REFRESH_STATIONS_METADATA_CRON !== "") {
  logger.info(
    "APP_REFRESH_STATIONS_METADATA_CRON: ",
    PROJECT_ENV.APP_REFRESH_STATIONS_METADATA_CRON
  );

  cron.schedule(PROJECT_ENV.APP_REFRESH_STATIONS_METADATA_CRON, () => {
    logger.info("Starting to refresh stations metadata..");

    refreshStationsMetadata()
      .then((result) => {
        logger.info("Stations metadata have been refreshed.", result);
      })
      .catch((error) => {
        logger.info("Stations metadata refresh has encountered an error:");
        logger.error(error.toString());
      });
  });
}

if (PROJECT_ENV.APP_REFRESH_STATIONS_RSS_FEED_CRON !== "") {
  logger.info(
    "APP_REFRESH_STATIONS_RSS_FEED_CRON: ",
    PROJECT_ENV.APP_REFRESH_STATIONS_RSS_FEED_CRON
  );

  cron.schedule(PROJECT_ENV.APP_REFRESH_STATIONS_RSS_FEED_CRON, () => {
    logger.info("Starting to refresh stations rss feed..");

    refreshStationsRssFeed()
      .then((result) => {
        logger.info("Stations rss feed have been refreshed.", result);
      })
      .catch((error) => {
        logger.info("Stations rss feed refresh has encountered an error:");
        logger.error(error.toString());
      });
  });
}

app.listen(port, () => {
  logger.info(`Server is running on port ${port}.`);
});

refreshStationsMetadata()
  .then((result) => {
    logger.info("Stations metadata have been refreshed.", result);
  })
  .catch((error) => {
    logger.info("Stations metadata refresh has encountered an error:");
    logger.error(error.toString());
  });

refreshStationsRssFeed()
  .then((result) => {
    logger.info("Stations rss feed have been refreshed.", result);
  })
  .catch((error) => {
    logger.info("Stations rss feed refresh has encountered an error:");
    logger.error(error.toString());
  });