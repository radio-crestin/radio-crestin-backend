import {Promise as BluebirdPromise} from "bluebird";
import {Station, StationNowPlaying, StationRssFeed, StationUptime} from "@/types";
import axios, {AxiosRequestConfig} from "axios";
import {PROJECT_ENV} from "@/env";
import {Logger} from "tslog";
import {getStations} from "@/services/getStations";

const logger: Logger = new Logger({name: "stationScrape"});

const statsFormatter = (stats: StationNowPlaying) => {
    if (stats.current_song !== null) {
        const allowedCharacters = /[^a-zA-ZÀ-žaâăáeéèiîoóöőøsșşșştțţțţ\-\s?'&]/g;

        // TODO: if name has fewer than 3 characters set it to empty
        // Decode Unicode special chars
        if(!!stats.current_song.name && stats.current_song.name !== "undefined" && stats.current_song?.name?.length > 2) {
            stats.current_song.name = stats.current_song.name
                .replace(/&#(\d+);/g, function (match, dec) {
                    return String.fromCharCode(dec);
                })
                .replace("_", " ")
                .replace("  ", " ")
                .replace(allowedCharacters, "")
                .replace("undefined", "")
                .replace(/^[a-z]/, function (m) {
                    return m.toUpperCase();
                });
        } else {
            stats.current_song.name = null;
        }

        if(!!stats.current_song.artist && stats.current_song.artist !== "undefined" && stats.current_song?.artist?.length > 2) {
            stats.current_song.artist = stats.current_song.artist
                .replace(/&#(\d+);/g, function (match, dec) {
                    return String.fromCharCode(dec);
                })
                .replace("_", " ")
                .replace("  ", " ")
                .replace(allowedCharacters, "")
                .replace("undefined", "")
                .replace(/^[a-z]/, function (m) {
                    return m.toUpperCase();
                });
        } else {
            stats.current_song.artist = null;
        }

        if(!stats.current_song.thumbnail_url || stats.current_song.thumbnail_url === "undefined" || stats.current_song?.thumbnail_url?.length < 2) {
            stats.current_song.thumbnail_url = null;
        }
    }

    return stats;
};

const extractNowPlaying = async ({
    url,
    headers,
    statsExtractor,
}: { url: string, headers?: any, statsExtractor: (data: any) => StationNowPlaying }): Promise<StationNowPlaying> => {
    logger.info("Extracting now playing: ", url);

    const options: AxiosRequestConfig = {
        method: "GET",
        url,
        headers,
    };

    return axios.request(options)
        .then(response => {
            return response.data;
        })
        .then(async (data) => {
            return {
                ...statsFormatter(statsExtractor(data)),
                raw_data: data,
            };
        })
        .catch(error => {
            logger.error(`Cannot extract stats from ${url}. error:`, error.toString());
            return {
                timestamp: (new Date()).toISOString(),
                current_song: null,
                listeners: null,
                raw_data: {},
                error: JSON.parse(JSON.stringify(error, Object.getOwnPropertyNames(error))),
            };
        });
};

const extractShoutcastNowPlaying = async ({shoutcast_stats_url}: { shoutcast_stats_url: string }): Promise<StationNowPlaying> => {
    return extractNowPlaying({
        url: shoutcast_stats_url,
        headers: {
            "content-type": "application/json;charset=UTF-8",
        },
        statsExtractor: (data) => {
            const [firstPart, lastPart] = data["songtitle"]?.split(" - ") || ["", ""];
            let songName, artist;

            if (firstPart && lastPart) {
                songName = lastPart;
                artist = firstPart;
            } else {
                songName = firstPart;
                artist = "";
            }
            return {
                timestamp: (new Date()).toISOString(),
                current_song: {
                    name: songName?.trim(),
                    artist: artist?.trim(),
                    thumbnail_url: null,
                } || null,
                listeners: data["currentlisteners"] || null,
            };
        },
    });
};

const extractRadioCoNowPlaying = async ({radio_co_stats_url}: { radio_co_stats_url: string }): Promise<StationNowPlaying> => {
    return extractNowPlaying({
        url: radio_co_stats_url,
        headers: {
            "content-type": "application/json;charset=UTF-8",
        },
        statsExtractor: (data) => {
            const [firstPart, lastPart] = data?.current_track?.title?.split(" - ") || ["", ""];
            let songName, artist;

            if (firstPart && lastPart) {
                artist = firstPart;
                songName = lastPart;
            } else {
                songName = firstPart;
                artist = "";
            }
            return {
                timestamp: (new Date()).toISOString(),
                current_song: {
                    name: songName?.trim(),
                    artist: artist?.trim(),
                    thumbnail_url: null,
                } || null,
                listeners: data["currentlisteners"] || null,
            };
        },
    });
};

const extractIcecastNowPlaying = async ({icecast_stats_url}: { icecast_stats_url: string }): Promise<StationNowPlaying> => {
    return extractNowPlaying({
        url: icecast_stats_url,
        headers: {
            "content-type": "application/json;charset=UTF-8",
        },
        statsExtractor: (data) => {
            const listenurl = /listen_url=(?<listen_url>.+)/gmi.exec(icecast_stats_url)?.groups?.listen_url || "";

            const source = data["icestats"]["source"].find((source: any) => source.listenurl.includes(listenurl));

            const [firstPart, lastPart] = source["title"]?.split(" - ") || ["", ""];
            let songName, artist;

            if (firstPart && lastPart) {
                artist = firstPart;
                songName = lastPart;
            } else {
                songName = firstPart;
                artist = "";
            }
            return {
                timestamp: (new Date()).toISOString(),
                current_song: {
                    name: songName?.trim(),
                    artist: artist?.trim(),
                    thumbnail_url: null,
                } || null,
                listeners: source["listeners"] || null,
            };
        },
    });
};

const extractShoutcastXmlNowPlaying = async ({shoutcast_xml_stats_url}: { shoutcast_xml_stats_url: string }): Promise<StationNowPlaying> => {
    return extractNowPlaying({
        url: shoutcast_xml_stats_url,
        headers: {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "cache-control": "max-age=0",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "sec-gpc": "1",
            "upgrade-insecure-requests": "1",
        },
        statsExtractor: (xml_page) => {
            const regex = /<(?<param_data>[a-zA-Z\s]+)>(?<value>(.*?))<\//mg;

            const data: any = {};
            let m;
            xml_page = xml_page.replace("SHOUTCASTSERVER", "");

            while ((m = regex.exec(xml_page)) !== null) {
                // This is necessary to avoid infinite loops with zero-width matches
                if (m.index === regex.lastIndex) {
                    regex.lastIndex++;
                }

                if (m?.groups?.param_data) {
                    data[m?.groups?.param_data] = m?.groups?.value;
                }
            }

            const [firstPart, lastPart] = data["SONGTITLE"]?.split(" - ") || ["", ""];
            let songName, artist;

            if (firstPart && lastPart) {
                artist = firstPart;
                songName = lastPart;
            } else {
                songName = firstPart;
                artist = "";
            }
            return {
                timestamp: (new Date()).toISOString(),
                current_song: {
                    name: songName?.trim(),
                    artist: artist?.trim(),
                    thumbnail_url: null,
                } || null,
                listeners: data["CURRENTLISTENERS"] || null,
            };
        },
    });
};

const extractOldIcecastHtmlNowPlaying = async ({old_icecast_html_stats_url}: { old_icecast_html_stats_url: string }): Promise<StationNowPlaying> => {
    return extractNowPlaying({
        url: old_icecast_html_stats_url,
        headers: {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "cache-control": "max-age=0",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "sec-gpc": "1",
            "upgrade-insecure-requests": "1",
        },
        statsExtractor: (html_page) => {
            const regex = /<td>(?<param_data>[a-zA-Z\s]+):<\/td>\n<td class="streamdata">(?<value>.*)<\/td>/gm;

            const data: any = {};
            let m;

            while ((m = regex.exec(html_page)) !== null) {
                // This is necessary to avoid infinite loops with zero-width matches
                if (m.index === regex.lastIndex) {
                    regex.lastIndex++;
                }

                if (m?.groups?.param_data) {
                    data[m?.groups?.param_data] = m?.groups?.value;
                }
            }

            const [firstPart, lastPart] = data["Current Song"]?.split(" - ") || ["", ""];
            let songName, artist;

            if (firstPart && lastPart) {
                artist = firstPart;
                songName = lastPart;
            } else {
                songName = firstPart;
                artist = "";
            }
            return {
                timestamp: (new Date()).toISOString(),
                current_song: {
                    name: songName?.trim(),
                    artist: artist?.trim(),
                    thumbnail_url: null,
                } || null,
                listeners: data["Current Listeners"] || null,
            };
        },
    });
};

const extractOldShoutcastHtmlNowPlaying = async ({old_shoutcast_stats_html_url}: { old_shoutcast_stats_html_url: string }): Promise<StationNowPlaying> => {
    return extractNowPlaying({
        url: old_shoutcast_stats_html_url,
        headers: {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "cache-control": "max-age=0",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "sec-gpc": "1",
            "upgrade-insecure-requests": "1",
        },
        statsExtractor: (html_page) => {
            const regex = /<tr><td width=100 nowrap><font class=default>(?<param_data>[a-zA-Z\s]+): <\/font><\/td><td><font class=default><b>(?<param_value>(.*?))<\/b><\/td><\/tr>/gmi;

            const data: any = {};
            let m;

            while ((m = regex.exec(html_page)) !== null) {
                // This is necessary to avoid infinite loops with zero-width matches
                if (m.index === regex.lastIndex) {
                    regex.lastIndex++;
                }

                if (m?.groups?.param_data) {
                    data[m?.groups?.param_data] = m?.groups?.value;
                }
            }

            const [firstPart, lastPart] = /\((?<listeners>[0-9+]) unique\)/gmi.exec(data["Stream Status"])?.groups?.listeners?.split(" - ") || ["", ""];
            let songName, artist;

            if (firstPart && lastPart) {
                artist = firstPart;
                songName = lastPart;
            } else {
                songName = firstPart;
                artist = "";
            }
            return {
                timestamp: (new Date()).toISOString(),
                current_song: {
                    name: songName?.trim(),
                    artist: artist?.trim(),
                    thumbnail_url: null,
                } || null,
                listeners: data["Current Listeners"] || null,
            };
        },
    });
};

const extractAripiSpreCerNowPlaying = async ({aripisprecer_url}: { aripisprecer_url: string }): Promise<StationNowPlaying> => {
    return extractNowPlaying({
        url: aripisprecer_url,
        headers: {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "cache-control": "max-age=0",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "sec-gpc": "1",
            "upgrade-insecure-requests": "1",
        },
        statsExtractor: (json_response) => {
            return {
                timestamp: (new Date()).toISOString(),
                current_song: {
                    name: json_response.title,
                    artist: json_response.artist,
                    thumbnail_url: json_response.picture !== ""? json_response.picture : null,
                } || null,
                listeners: null,
            };
        },
    });
};

const getStationUptime = ({station}: { station: Station }): Promise<StationUptime> => {
    logger.info("Checking uptime of station: ", station.title);

    const start = process.hrtime();
    let responseStatus = -1;
    let latency_ms = -1;
    let responseHeaders: any = {};

    const options: AxiosRequestConfig = {
        method: "GET",
        url: station.stream_url,
        timeout: 5000,
        responseType: "stream",
        headers: {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "accept-language": "en-US,en;q=0.9,ro;q=0.8",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "sec-ch-ua": "\" Not;A Brand\";v=\"99\", \"Google Chrome\";v=\"97\", \"Chromium\";v=\"97\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Linux\"",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "cross-site",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
        },
    };

    return axios.request(options).then(async (response) => {
        responseStatus = response.status;
        responseHeaders = response.headers;

        // TODO: check if the audio volume is not 0 for at least 5-10 seconds

        latency_ms = Math.round(process.hrtime(start)[1] / 1000000);

        if (responseStatus !== 200) {
            return {
                timestamp: (new Date()).toISOString(),
                is_up: false,
                latency_ms,
                raw_data: {
                    responseHeaders,
                    responseStatus,
                },
            };
        }

        return {
            timestamp: (new Date()).toISOString(),
            is_up: true,
            latency_ms,
            raw_data: {
                responseHeaders,
                responseStatus,
            },
        };
    }).catch((error) => {
        logger.error(error.toString());
        return {
            timestamp: (new Date()).toISOString(),
            is_up: false,
            latency_ms: latency_ms,
            raw_data: {
                responseHeaders,
                responseStatus,
                error: error,
            },
        };
    });

};

const mergeStats = (a: any, b: any) => {
    a = JSON.parse(JSON.stringify(a));
    b = JSON.parse(JSON.stringify(b));

    Object.keys(b).forEach((key) => {
        if(b[key]) {
            if(typeof b[key] === "object") {
                a[key] = mergeStats(a[key] || {}, b[key]);
                return;
            }

            a[key] = b[key];
        }
    });
    return JSON.parse(JSON.stringify(a));
};

const getStationNowPlaying = async ({station}: { station: Station }): Promise<StationNowPlaying> => {
    let mergedStats: any = {
        timestamp: (new Date()).toISOString(),
        current_song: null,
        listeners: null,
        raw_data: {},
        error: null,
    };

    const station_metadata_fetches = station.station_metadata_fetches.sort((a, b) => a.order > b.order ? 1 : -1);

    for (let i = 0; i < station_metadata_fetches.length; i++) {
        const stationMetadataFetcher = station_metadata_fetches[i];
        let stats: any = {};

        if (stationMetadataFetcher.station_metadata_fetch_category.slug === "shoutcast") {
            stats = await extractShoutcastNowPlaying({shoutcast_stats_url: stationMetadataFetcher.url});
        }

        if (stationMetadataFetcher.station_metadata_fetch_category.slug === "radio_co") {
            stats =  await extractRadioCoNowPlaying({radio_co_stats_url: stationMetadataFetcher.url});
        }

        if (stationMetadataFetcher.station_metadata_fetch_category.slug === "icecast") {
            stats =  await extractIcecastNowPlaying({icecast_stats_url: stationMetadataFetcher.url});
        }

        if (stationMetadataFetcher.station_metadata_fetch_category.slug === "shoutcast_xml") {
            stats =  await extractShoutcastXmlNowPlaying({shoutcast_xml_stats_url: stationMetadataFetcher.url});
        }

        if (stationMetadataFetcher.station_metadata_fetch_category.slug === "old_icecast_html") {
            stats =  await extractOldIcecastHtmlNowPlaying({old_icecast_html_stats_url: stationMetadataFetcher.url});
        }

        if (stationMetadataFetcher.station_metadata_fetch_category.slug === "old_shoutcast_html") {
            stats =  await extractOldShoutcastHtmlNowPlaying({old_shoutcast_stats_html_url: stationMetadataFetcher.url});
        }

        if (stationMetadataFetcher.station_metadata_fetch_category.slug === "aripisprecer_api") {
            stats =  await extractAripiSpreCerNowPlaying({aripisprecer_url: stationMetadataFetcher.url});
        }

        mergedStats = mergeStats(mergedStats, stats);

    }
    return JSON.parse(JSON.stringify(mergedStats));
};

const updateStationMetadata = async ({
    station,
    stationNowPlaying,
    stationUptime,
}: { station: Station, stationNowPlaying: StationNowPlaying, stationUptime: StationUptime }): Promise<boolean> => {
    const escapedStationNowPlayingRawData = JSON.stringify(JSON.stringify(stationNowPlaying.raw_data));

    const escapedStationNowPlayingError = JSON.stringify(JSON.stringify(stationNowPlaying.error));

    const escapedStationUptimeRawData = JSON.stringify(JSON.stringify(stationUptime.raw_data));

    const query = `mutation UpdateStationMetadata {
  insert_stations_now_playing_one(
    object: {
      station_id: ${station.id}
      timestamp: "${stationNowPlaying.timestamp}"
      song: { 
        data: { 
            name: ${!stationNowPlaying?.current_song?.name ? null: "\"" + stationNowPlaying.current_song.name + "\""}
            artist: {
                data: {
                    name: ${!stationNowPlaying?.current_song?.artist ? null: "\"" + stationNowPlaying.current_song.artist + "\""}
                }, 
                on_conflict: {
                    constraint: artists_name_key, 
                    update_columns: name
                }
            }
            thumbnail_url: ${!stationNowPlaying?.current_song?.thumbnail_url ? null: "\"" + stationNowPlaying.current_song.thumbnail_url + "\""}
        } 
        on_conflict: {
          constraint: songs_name_artist_id_key
          update_columns: [thumbnail_url]
        }
      }
      listeners: ${!stationNowPlaying?.listeners ? null: "\"" + stationNowPlaying.listeners + "\""}
      raw_data: ${escapedStationNowPlayingRawData || null}
      error: ${escapedStationNowPlayingError || null}
    }
  ) {
    id
  }
  insert_stations_uptime_one(
    object: { 
        station_id: ${station.id}, 
        timestamp: "${stationUptime.timestamp}", 
        is_up: ${stationUptime.is_up}, 
        latency_ms: ${stationUptime.latency_ms}, 
        raw_data: ${escapedStationUptimeRawData} 
    }
  ) {
    id
  }
}
`;

    const options: AxiosRequestConfig = {
        method: "POST",
        url: PROJECT_ENV.APP_GRAPHQL_ENDPOINT_URI,
        headers: {
            "content-type": "application/json",
            "x-hasura-admin-secret": PROJECT_ENV.APP_GRAPHQL_ADMIN_SECRET,
        },
        timeout: 5000,
        data: {
            operationName: "UpdateStationMetadata",
            query: query,
            variables: {},
        },
    };

    return axios.request(options).then(function (response) {
        if (!response.data || response.data.errors) {
            throw new Error(`Invalid response ${response.status}: ${JSON.stringify(response.data)}, query: ${query}`);
        }

        return typeof response.data?.data?.insert_stations_now_playing_one?.id !== "undefined" && typeof response.data?.data?.insert_stations_uptime_one?.id !== "undefined";

    });
};

export const refreshStationsMetadata = async () => {
    const stations: Station[] = await getStations();

    return BluebirdPromise.map(stations.sort( () => .5 - Math.random() ), async (station: Station) => {
        const stationNowPlaying: StationNowPlaying = await getStationNowPlaying({station});

        const stationUptime = await getStationUptime({station});

        // TODO: implement a mechanism to save in DB just the changes
        const done = await updateStationMetadata({station, stationNowPlaying, stationUptime});

        return {
            stationId: station.id,
            done: done,
        };
    },
    {
        concurrency: 10,
    },
    );

};
