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
    }
  });
}

export const getStationsData = async (): Promise<StationData[]> => {
  if (Object.values(STATION_STATS_BY_STATION_ID_CACHE).length == 0) {
    await refreshStationsStats();
  }
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
      stats: {
        ...STATION_STATS_BY_STATION_ID_CACHE[station.id]?.stats,
      }
    }
  });
}


export default async function handler(req: any, res: any) {
  res.status(200).json({stations: await getStationsData()})
}
