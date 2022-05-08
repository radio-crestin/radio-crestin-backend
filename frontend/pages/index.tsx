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
  const router = useRouter()
  const { stations, station_groups, isLoading, isError } = useStations({
    refreshInterval: 10000,
    initialStationsMetadata: stations_metadata,
  });

  const random = (a: any[]) => a.find((_, i, ar) => Math.random() < 1 / (ar.length - i))

  const [selectedStationSlug, selectStationSlug] = useLocalStorageState(
    null,
    "SELECTED_STATION_SLUG",
  );

  const [selectedStationGroupSlug, selectStationGroupSlug] = useLocalStorageState(
    null,
    "SELECTED_STATION_GROUP_SLUG",
  );
  // if(selectedStationSlug !== null && selectedStationGroupSlug !== null) {
  //   router.push(
  //     {
  //       pathname: `/[station_category_slug]/[station_name_slug]`,
  //       query: {
  //         station_category_slug: selectedStationGroupSlug,
  //         station_name_slug: selectedStationSlug
  //       }
  //     },
  //     `/${selectedStationGroupSlug}/${selectedStationSlug}`,
  //     {shallow: false}
  //   );
  //   return <></>
  // } else {
  //
  // }
  useEffect(() => {

    selectStationSlug(stations[0].slug);
    selectStationGroupSlug(station_groups[0].slug);
  }, [])
  return StationPage({
    stations_metadata,
    station_category_slug: station_groups[0].slug,
    station_slug: stations[0].slug
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
