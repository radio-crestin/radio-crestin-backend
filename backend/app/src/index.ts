import express, {NextFunction, Request, Response} from 'express';
import {refreshStationsMetadata} from "./services/stationScrape";
import {Logger} from "tslog";
import {PROJECT_ENV} from "./env";
import * as cron from "node-cron"

const app = express();
const port = PROJECT_ENV.APP_SERVER_PORT;

const logger: Logger = new Logger({name: "index"});

app.get('/', async (request: Request, response: Response, next: NextFunction) => {
    response.status(200).json({up: true});
});

app.get('/refreshStationsMetadata', (request: Request, response: Response, next: NextFunction) => {
    refreshStationsMetadata().then(result => {
        response.status(200).json({result});
    }).catch(error => {
        logger.prettyError(error);
        response.status(500).json({error});
    })
});

cron.schedule(PROJECT_ENV.APP_REFRESH_STATIONS_METADATA_CRON, () => {
    logger.info('Starting to refresh stations metadata..');
    refreshStationsMetadata().then(result => {
        logger.info('Stations metadata have been refreshed.', result);
    }).catch(error => {
        logger.info('Stations metadata refresh has encountered an error:');
        logger.prettyError(error);
    })
});

app.listen(port, () => {
    console.log(`Server is running on port ${port}.`);
});