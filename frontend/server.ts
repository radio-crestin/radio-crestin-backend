import {PROJECT_ENV} from "./utils/env";

const {parse} = require('url')
const express = require('express')
const next = require('next')
const cookieSession = require('cookie-session')

const dev = process.env.NODE_ENV !== 'production'
const port = parseInt(process.env.FRONTEND_SERVER_PORT || "3000");
const app = next({dev, hostname: "0.0.0.0", port})
const handle = app.getRequestHandler();
const {Logger} = require("tslog")

const logger = new Logger({name: "server"});

app.prepare().then(() => {
  const server = express();

  server.use(cookieSession({
    name: 'session.sid',
    keys: [PROJECT_ENV.FRONTEND_COOKIE_SECRET],

    // Cookie Options
    maxAge: 30 * 24 * 60 * 60 * 1000 // 30 days
  }))

  server.all('*', (req: Request, res: Response) => {
    const parsedUrl = parse(req.url, true)
    return handle(req, res, parsedUrl)
  })

  server.listen(port, (err: Error) => {
    if (err) throw err
    logger.info(`> Ready on http://localhost:${port}`)
  })
})

