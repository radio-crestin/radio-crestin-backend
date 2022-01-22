import {refreshStationsStatsIfExpired} from "./refresh";
import {STATIONS} from "../../../../constants";
import {STATION_STATS_BY_STATION_ID_CACHE} from "./index";

export const getStationsUptime = async () => {
  await refreshStationsStatsIfExpired();
  return STATIONS.map(station => {
    const isUp = STATION_STATS_BY_STATION_ID_CACHE[station.id]?.streamStatus?.up;
    return {
      id: station.id,
      title: station.title,
      isUpMessage: isUp ? `${station.title} is up` : `${station.title} is down`,
      website: station.website,
      contact: station.contact,
      stream_url: station.stream_url,
      streamStatus: {
        ...STATION_STATS_BY_STATION_ID_CACHE[station.id]?.streamStatus,
      }
    }
  });
}

export default async function handler(req: any, res: any) {
  res.status(200).json({stations: await getStationsUptime()})
}
