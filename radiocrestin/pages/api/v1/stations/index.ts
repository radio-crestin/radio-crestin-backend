import {STATIONS} from '../../../../constants';
import {StationData, StationStatsByStationId} from "types";
import {refreshStationsStats} from "./refresh";

export const STATION_STATS_BY_STATION_ID_CACHE: StationStatsByStationId = {};

export const getStaticStationsData = (): StationData[] => {
  return STATIONS.map(station => {
    return {
      id: station.id,
      order: station.order,
      title: station.title,
      website: station.website,
      contact: station.contact,
      stream_url: station.stream_url,
      thumbnail_url: station.thumbnail_url,
      groups: station.groups,
      uptime: {},
      stats: {}
    }
  });
}

export const getStationsData = async (): Promise<StationData[]> => {
  if (Object.values(STATION_STATS_BY_STATION_ID_CACHE).length == 0) {
    await refreshStationsStats();
  }
  return STATIONS.map(station => {
    const streamStatus = STATION_STATS_BY_STATION_ID_CACHE[station.id]?.streamStatus;
    return {
      id: station.id,
      order: station.order,
      title: station.title,
      website: station.website,
      contact: station.contact,
      stream_url: station.stream_url,
      thumbnail_url: station.thumbnail_url,
      groups: station.groups,
      uptime: {
        up: streamStatus?.up,
        latency_ms: streamStatus?.latencyMs,
        status_message: streamStatus?.up ? `${station.title} is up` : `${station.title} is down`,
      },
      stats: {
        ...STATION_STATS_BY_STATION_ID_CACHE[station.id]?.stats,
      }
    }
  });
}


export default async function handler(req: any, res: any) {
  res.status(200).json({stations: await getStationsData()})
}
