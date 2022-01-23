import {StationData} from "../../../../../types";
import {refreshStationsStatsIfExpired} from "../refresh";
import {STATIONS} from "../../../../../constants";
import {STATION_STATS_BY_STATION_ID_CACHE} from "../index";

export const getStationsUptime = async () => {
  await refreshStationsStatsIfExpired();
  let r: { [key: string]: any } = {};
  STATIONS.forEach((station: StationData) => {
    const streamStatus = STATION_STATS_BY_STATION_ID_CACHE[station.id]?.streamStatus;
    r[station.id] = {
      id: station.id,
      title: station.title,
      website: station.website,
      contact: station.contact,
      stream_url: station.stream_url,
      uptime: {
        up: streamStatus?.up,
        latency_ms: streamStatus?.latencyMs,
        status_message: streamStatus?.up ? `${station.title} is up` : `${station.title} is down`,
      },
      streamStatus: {
        ...STATION_STATS_BY_STATION_ID_CACHE[station.id]?.streamStatus,
      }
    }
  })
  return r;
}

export default async function handler(req: any, res: any) {
  res.status(200).json({stations: await getStationsUptime()})
}
