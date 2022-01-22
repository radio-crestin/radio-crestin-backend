import useSWR from "swr";
import {StationData} from "../types";

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

  return {
    stationsData,
    isLoading: !error && !data,
    isError: error
  }
}
