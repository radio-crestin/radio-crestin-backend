import express, {NextFunction, Request, Response} from "express";
import {refreshStationsMetadata} from "./services/stationScrape";
import {Logger} from "tslog";
import {PROJECT_ENV} from "./env";
import * as cron from "node-cron";
import {refreshStationsRssFeed} from "./services/stationRssFeedScrape";

const app = express();

const port = PROJECT_ENV.APP_SERVER_PORT;

const logger: Logger = new Logger({name: "index"});

app.get("/", async (request: Request, response: Response, next: NextFunction) => {
    response.status(200).json({up: true});
});

app.get("/refreshStationsMetadata", (request: Request, response: Response, next: NextFunction) => {
    refreshStationsMetadata().then(result => {
        response.status(200).json({result});
    }).catch(error => {
        logger.error(error.toString());
        response.status(500).json({error});
    });
});

app.get("/refreshStationsRssFeed", (request: Request, response: Response, next: NextFunction) => {
    refreshStationsRssFeed().then(result => {
        response.status(200).json({result});
    }).catch(error => {
        logger.error(error.toString());
        response.status(500).json({error});
    });
});

if(PROJECT_ENV.APP_REFRESH_STATIONS_METADATA_CRON !== "") {
    cron.schedule(PROJECT_ENV.APP_REFRESH_STATIONS_METADATA_CRON, () => {
        logger.info("Starting to refresh stations metadata..");

        refreshStationsMetadata().then(result => {
            logger.info("Stations metadata have been refreshed.", result);
        }).catch(error => {
            logger.info("Stations metadata refresh has encountered an error:");
            logger.error(error.toString());
        });
    });
}

if(PROJECT_ENV.APP_REFRESH_STATIONS_RSS_FEED_CRON !== "") {
    cron.schedule(PROJECT_ENV.APP_REFRESH_STATIONS_RSS_FEED_CRON, () => {
        logger.info("Starting to refresh stations rss feed..");

        refreshStationsRssFeed().then(result => {
            logger.info("Stations rss feed have been refreshed.", result);
        }).catch(error => {
            logger.info("Stations rss feed refresh has encountered an error:");
            logger.error(error.toString());
        });
    });
}

app.listen(port, () => {
    logger.info(`Server is running on port ${port}.`);
});