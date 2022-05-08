import React, {useEffect} from "react";
import { useStations } from "../hooks/stations";
import { useLocalStorageState } from "../utils/state";
import { getStationsMetadata } from "../backendServices/stations";
import { Station, StationsMetadata } from "../types";
import {useRouter} from "next/router";
import StationPage from "./[station_category_slug]/[station_slug]";

const groupBy = function(xs: any[], key: string) {
  return xs.reduce(function(rv, x) {
    rv[x[key]] = x;
    return rv;
  }, {});
};

export default function Home({stations_metadata}: {
  stations_metadata: StationsMetadata;
}) {
  const { stations, station_groups, isLoading, isError } = useStations({
    refreshInterval: 10000,
    initialStationsMetadata: stations_metadata,
  });
  return StationPage({
    stations_metadata,
    station_category_slug: station_groups[0].slug,
    station_slug: stations[0].slug,
    default_station: true
  })
}

export async function getServerSideProps() {
  const stations_metadata = await getStationsMetadata();
  return {
    props: {
      stations_metadata,
    },
  };
}
