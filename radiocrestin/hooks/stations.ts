import useSWR from "swr";
import {StationData, StationGroup} from "../types";

const fetcher = (url: string) => fetch(url).then((res) => res.json())

export const useStations = (
  {
    refreshInterval,
    initialStationsData
  }: {
    refreshInterval: number,
    initialStationsData: StationData[]
  }
) => {
  const {data, error} = useSWR('/api/v1/stations', fetcher, {
    refreshInterval: refreshInterval
  });
  if (error) {
    console.error("An error has occurred fetching stations data. Please retry later!");
  }

  let stationsData: StationData[];
  if (!data) {
    stationsData = initialStationsData;
  } else {
    stationsData = data["stations"];
  }
  stationsData = stationsData || [];

  stationsData = stationsData.sort(s => s.order);

  const stationGroups: { [key: string]: StationGroup } = {};
  stationsData.forEach(station => {
    station.groups.forEach(group => {
      if (typeof stationGroups[group] === "undefined") {
        stationGroups[group] = {
          groupName: group,
          stationsData: [station],
        }
      } else {
        stationGroups[group].stationsData.push(station);
      }
    })
  });

  // TODO: invalidate stats if timestamp is older than 5 minutes

  return {
    stationsData,
    stationGroups,
    isLoading: !error && !data,
    isError: error
  }
}
