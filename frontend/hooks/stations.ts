import useSWR from "swr";
import { StationsMetadata } from "../types";

const fetcher = (url: string) => fetch(url).then(r => r.json());

export const useStations = ({
  refreshInterval,
  initialStationsMetadata,
}: {
  refreshInterval: number;
  initialStationsMetadata: StationsMetadata;
}) => {
  const { data, error } = useSWR("/api/v1/stations", fetcher, {
    refreshInterval: refreshInterval,
  });

  if (error) {
    console.error(
      "An error has occurred fetching stations metadata. Please try again later!",
    );
  }

  let stationsMetadata: StationsMetadata;

  if (data) {
    stationsMetadata = data;
  } else {
    stationsMetadata = initialStationsMetadata;
  }

  // TODO: invalidate now_playing if timestamp is older than 5 minutes

  return {
    stations: stationsMetadata.stations.sort((a,b) => a.order > b.order?1:-1),
    station_groups: stationsMetadata.station_groups.sort((a,b) => a.order > b.order?1:-1),
    isLoading: !error && !data,
    isError: error,
  };
};
