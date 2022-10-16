import React from "react";
import { useStations } from "../hooks/stations";
import { getStationsMetadata } from "../backendServices/stations";
import { StationsMetadata } from "../types";
import StationPage from "./[station_category_slug]/[station_slug]";

const groupBy = function(xs: any[], key: string) {
  return xs.reduce(function(rv, x) {
    rv[x[key]] = x;
    return rv;
  }, {});
};

export default function Home({ stations_metadata, hostname }: {
  stations_metadata: StationsMetadata;
  hostname: string;
}) {
  const { stations, station_groups, isLoading, isError } = useStations({
    refreshInterval: 10000,
    initialStationsMetadata: stations_metadata,
  });
  return StationPage({
    hostname,
    stations_metadata,
    station_category_slug: station_groups[0].slug,
    station_slug: stations[0].slug,
    default_station: true,
  });
}

export async function getServerSideProps(context: any) {
  const stations_metadata = await getStationsMetadata();
  const { req } = context;
  return {
    props: {
      stations_metadata,
      hostname: req.headers.host,
    },
  };
}
