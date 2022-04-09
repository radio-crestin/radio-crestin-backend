const {createServer} = require('http')
const {parse} = require('url')
const next = require('next')

const dev = process.env.NODE_ENV !== 'production'
const app = next({dev})
const handle = app.getRequestHandler();
const {Logger} = require("tslog")

const logger = new Logger({name: "server"});

app.prepare().then(() => {
  createServer((req, res) => {
    // Be sure to pass `true` as the second argument to `url.parse`.
    // This tells it to parse the query portion of the URL.
    const parsedUrl = parse(req.url, true)
    // const { pathname, query } = parsedUrl

    handle(req, res, parsedUrl)
  }).listen(parseInt(process.env.FRONTEND_SERVER_PORT || "3000"), (err) => {
    if (err) throw err
    logger.info(`> Ready on http://localhost:${parseInt(process.env.FRONTEND_SERVER_PORT || "3000")}`)
  })
})
