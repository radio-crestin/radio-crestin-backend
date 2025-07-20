import express, { NextFunction, Request, Response } from "express";
import { Logger } from "tslog";
import { PROJECT_ENV } from "./env";
import axios from "axios";
import {authorizationService} from "./services/authorizationService";
import cookieParser from "cookie-parser";

const app = express();

const port = PROJECT_ENV.AUTH_SERVER_PORT;

const logger: Logger<any> = new Logger({ name: "index", minLevel: PROJECT_ENV.AUTH_DEBUG? 2: 3 });

// Axios config
axios.defaults.timeout = 10 * 1000;

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

app.listen(port, () => {
  logger.info(`Server is running on port ${port}.`);
});
