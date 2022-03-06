"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.refreshStationsMetadata = void 0;
const bluebird_1 = require("bluebird");
const node_abort_controller_1 = require("node-abort-controller");
const axios_1 = __importDefault(require("axios"));
const env_1 = require("../env");
const statsFormatter = (stats) => {
    var _a, _b, _c, _d;
    if (stats.current_song) {
        const allowedCharacters = /[^a-zA-ZÀ-žaâăáeéèiîoóöőøsșşșştțţțţ\-\s?'&]/g;
        // TODO: if name has fewer than 3 characters set it to empty
        // Decode Unicode special chars
        stats.current_song = {
            name: stats.current_song.name
                .replace(/&#(\d+);/g, function (match, dec) {
                return String.fromCharCode(dec);
            })
                .replace("_", " ")
                .replace("  ", " ")
                .replace(allowedCharacters, "")
                .replace(/^[a-z]/, function (m) {
                return m.toUpperCase();
            }),
            artist: stats.current_song.artist
                .replace(/&#(\d+);/g, function (match, dec) {
                return String.fromCharCode(dec);
            })
                .replace("_", " ")
                .replace("  ", " ")
                .replace(allowedCharacters, "")
                .replace(/^[a-z]/, function (m) {
                return m.toUpperCase();
            }),
        };
    }
    if (((_b = (_a = stats.current_song) === null || _a === void 0 ? void 0 : _a.name) === null || _b === void 0 ? void 0 : _b.length) && ((_d = (_c = stats.current_song) === null || _c === void 0 ? void 0 : _c.name) === null || _d === void 0 ? void 0 : _d.length) < 3) {
        if (stats.current_song) {
            stats.current_song.name = "";
        }
    }
    return stats;
};
const extractNowPlaying = ({ url, headers, statsExtractor, decodeJson }) => __awaiter(void 0, void 0, void 0, function* () {
    let raw_data = undefined;
    return fetch(url, {
        headers: headers,
        body: null,
        method: "GET"
    })
        .then(response => {
        try {
            if (decodeJson) {
                raw_data = response.json();
                return raw_data;
            }
        }
        catch (e) {
            console.error("Invalid JSON response: ", response.text());
        }
        raw_data = response.text();
        return raw_data;
    })
        .then((data) => __awaiter(void 0, void 0, void 0, function* () {
        return Object.assign(Object.assign({}, statsFormatter(statsExtractor(data))), { raw_data: data });
    }))
        .catch(error => {
        console.error(`Cannot extract stats from ${url}. error:`, error);
        return {
            timestamp: (new Date()).toISOString(),
            current_song: null,
            listeners: null,
            raw_data: {},
            error: JSON.parse(JSON.stringify(error, Object.getOwnPropertyNames(error)))
        };
    });
});
const extractShoutcastNowPlaying = ({ shoutcast_stats_url }) => __awaiter(void 0, void 0, void 0, function* () {
    return extractNowPlaying({
        url: shoutcast_stats_url,
        headers: {
            "content-type": "application/json;charset=UTF-8",
        },
        decodeJson: true,
        statsExtractor: (data) => {
            var _a;
            const [firstPart, lastPart] = ((_a = data["songtitle"]) === null || _a === void 0 ? void 0 : _a.split(" - ")) || ["", ""];
            let songName, artist;
            if (firstPart && lastPart) {
                songName = lastPart;
                artist = firstPart;
            }
            else {
                songName = firstPart;
                artist = "";
            }
            return {
                timestamp: (new Date()).toISOString(),
                current_song: {
                    name: songName === null || songName === void 0 ? void 0 : songName.trim(),
                    artist: artist === null || artist === void 0 ? void 0 : artist.trim()
                } || null,
                listeners: data["currentlisteners"] || null,
            };
        }
    });
});
const extractRadioCoNowPlaying = ({ radio_co_stats_url }) => __awaiter(void 0, void 0, void 0, function* () {
    return extractNowPlaying({
        url: radio_co_stats_url,
        headers: {
            "content-type": "application/json;charset=UTF-8",
        },
        decodeJson: true,
        statsExtractor: (data) => {
            var _a;
            const [firstPart, lastPart] = ((_a = data["current_track"]["title"]) === null || _a === void 0 ? void 0 : _a.split(" - ")) || ["", ""];
            let songName, artist;
            if (firstPart && lastPart) {
                artist = firstPart;
                songName = lastPart;
            }
            else {
                songName = firstPart;
                artist = "";
            }
            return {
                timestamp: (new Date()).toISOString(),
                current_song: {
                    name: songName === null || songName === void 0 ? void 0 : songName.trim(),
                    artist: artist === null || artist === void 0 ? void 0 : artist.trim()
                } || null,
                listeners: data["currentlisteners"] || null,
            };
        }
    });
});
const extractIcecastNowPlaying = ({ icecast_stats_url }) => __awaiter(void 0, void 0, void 0, function* () {
    return extractNowPlaying({
        url: icecast_stats_url,
        headers: {
            "content-type": "application/json;charset=UTF-8",
        },
        decodeJson: true,
        statsExtractor: (data) => {
            var _a, _b, _c;
            let listenurl = ((_b = (_a = /listen_url=(?<listen_url>.+)/gmi.exec(icecast_stats_url)) === null || _a === void 0 ? void 0 : _a.groups) === null || _b === void 0 ? void 0 : _b.listen_url) || "";
            let source = data["icestats"]["source"].find((source) => source.listenurl.includes(listenurl));
            const [firstPart, lastPart] = ((_c = source["title"]) === null || _c === void 0 ? void 0 : _c.split(" - ")) || ["", ""];
            let songName, artist;
            if (firstPart && lastPart) {
                artist = firstPart;
                songName = lastPart;
            }
            else {
                songName = firstPart;
                artist = "";
            }
            return {
                timestamp: (new Date()).toISOString(),
                current_song: {
                    name: songName === null || songName === void 0 ? void 0 : songName.trim(),
                    artist: artist === null || artist === void 0 ? void 0 : artist.trim()
                } || null,
                listeners: source["listeners"] || null,
            };
        }
    });
});
const extractShoutcastXmlNowPlaying = ({ shoutcast_xml_stats_url }) => __awaiter(void 0, void 0, void 0, function* () {
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
            "upgrade-insecure-requests": "1"
        },
        decodeJson: false,
        statsExtractor: (xml_page) => {
            var _a, _b, _c, _d;
            let regex = /<(?<param_data>[a-zA-Z\s]+)>(?<value>(.*?))<\//mg;
            let data = {};
            let m;
            xml_page = xml_page.replace("SHOUTCASTSERVER", "");
            while ((m = regex.exec(xml_page)) !== null) {
                // This is necessary to avoid infinite loops with zero-width matches
                if (m.index === regex.lastIndex) {
                    regex.lastIndex++;
                }
                if ((_a = m === null || m === void 0 ? void 0 : m.groups) === null || _a === void 0 ? void 0 : _a.param_data) {
                    data[(_b = m === null || m === void 0 ? void 0 : m.groups) === null || _b === void 0 ? void 0 : _b.param_data] = (_c = m === null || m === void 0 ? void 0 : m.groups) === null || _c === void 0 ? void 0 : _c.value;
                }
            }
            const [firstPart, lastPart] = ((_d = data["SONGTITLE"]) === null || _d === void 0 ? void 0 : _d.split(" - ")) || ["", ""];
            let songName, artist;
            if (firstPart && lastPart) {
                artist = firstPart;
                songName = lastPart;
            }
            else {
                songName = firstPart;
                artist = "";
            }
            return {
                timestamp: (new Date()).toISOString(),
                current_song: {
                    name: songName === null || songName === void 0 ? void 0 : songName.trim(),
                    artist: artist === null || artist === void 0 ? void 0 : artist.trim()
                } || null,
                listeners: data["CURRENTLISTENERS"] || null,
            };
        }
    });
});
const extractOldIcecastHtmlNowPlaying = ({ old_icecast_html_stats_url }) => __awaiter(void 0, void 0, void 0, function* () {
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
            "upgrade-insecure-requests": "1"
        },
        decodeJson: false,
        statsExtractor: (html_page) => {
            var _a, _b, _c, _d;
            let regex = /<td>(?<param_data>[a-zA-Z\s]+):<\/td>\n<td class="streamdata">(?<value>.*)<\/td>/gm;
            let data = {};
            let m;
            while ((m = regex.exec(html_page)) !== null) {
                // This is necessary to avoid infinite loops with zero-width matches
                if (m.index === regex.lastIndex) {
                    regex.lastIndex++;
                }
                if ((_a = m === null || m === void 0 ? void 0 : m.groups) === null || _a === void 0 ? void 0 : _a.param_data) {
                    data[(_b = m === null || m === void 0 ? void 0 : m.groups) === null || _b === void 0 ? void 0 : _b.param_data] = (_c = m === null || m === void 0 ? void 0 : m.groups) === null || _c === void 0 ? void 0 : _c.value;
                }
            }
            const [firstPart, lastPart] = ((_d = data["Current Song"]) === null || _d === void 0 ? void 0 : _d.split(" - ")) || ["", ""];
            let songName, artist;
            if (firstPart && lastPart) {
                artist = firstPart;
                songName = lastPart;
            }
            else {
                songName = firstPart;
                artist = "";
            }
            return {
                timestamp: (new Date()).toISOString(),
                current_song: {
                    name: songName === null || songName === void 0 ? void 0 : songName.trim(),
                    artist: artist === null || artist === void 0 ? void 0 : artist.trim()
                } || null,
                listeners: data["Current Listeners"] || null,
            };
        }
    });
});
const extractOldShoutcastHtmlNowPlaying = ({ old_shoutcast_stats_html_url }) => __awaiter(void 0, void 0, void 0, function* () {
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
            "upgrade-insecure-requests": "1"
        },
        decodeJson: false,
        statsExtractor: (html_page) => {
            var _a, _b, _c, _d, _e, _f;
            let regex = /<tr><td width=100 nowrap><font class=default>(?<param_data>[a-zA-Z\s]+): <\/font><\/td><td><font class=default><b>(?<param_value>(.*?))<\/b><\/td><\/tr>/gmi;
            let data = {};
            let m;
            while ((m = regex.exec(html_page)) !== null) {
                // This is necessary to avoid infinite loops with zero-width matches
                if (m.index === regex.lastIndex) {
                    regex.lastIndex++;
                }
                if ((_a = m === null || m === void 0 ? void 0 : m.groups) === null || _a === void 0 ? void 0 : _a.param_data) {
                    data[(_b = m === null || m === void 0 ? void 0 : m.groups) === null || _b === void 0 ? void 0 : _b.param_data] = (_c = m === null || m === void 0 ? void 0 : m.groups) === null || _c === void 0 ? void 0 : _c.value;
                }
            }
            const [firstPart, lastPart] = ((_f = (_e = (_d = /\((?<listeners>[0-9+]) unique\)/gmi.exec(data["Stream Status"])) === null || _d === void 0 ? void 0 : _d.groups) === null || _e === void 0 ? void 0 : _e.listeners) === null || _f === void 0 ? void 0 : _f.split(" - ")) || ["", ""];
            let songName, artist;
            if (firstPart && lastPart) {
                artist = firstPart;
                songName = lastPart;
            }
            else {
                songName = firstPart;
                artist = "";
            }
            return {
                timestamp: (new Date()).toISOString(),
                current_song: {
                    name: songName === null || songName === void 0 ? void 0 : songName.trim(),
                    artist: artist === null || artist === void 0 ? void 0 : artist.trim()
                } || null,
                listeners: data["Current Listeners"] || null,
            };
        }
    });
});
const fetchWithTimeout = function (url, options, timeout = 5000) {
    return __awaiter(this, void 0, void 0, function* () {
        const controller = new node_abort_controller_1.AbortController();
        setTimeout(() => controller.abort(), timeout);
        return fetch(url, Object.assign({ signal: controller.signal }, options));
    });
};
const getStationUptime = ({ station }) => {
    console.log(`Checking station uptime: ${station}`);
    let start = process.hrtime();
    let responseStatus = -1;
    let latency_ms = -1;
    let headers = {};
    return fetchWithTimeout(station.stream_url, {
        mode: 'no-cors',
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
            "upgrade-insecure-requests": "1"
        }
    }, 2000).then((response) => __awaiter(void 0, void 0, void 0, function* () {
        responseStatus = response.status;
        latency_ms = Math.round(process.hrtime(start)[1] / 1000000);
        headers = {};
        // @ts-ignore
        for (const header of response.headers.entries()) {
            headers[header[0]] = header[1];
        }
        headers = JSON.parse(JSON.stringify(headers));
        if (responseStatus !== 200) {
            let textResponse = "";
            try {
                textResponse = yield response.text();
            }
            catch (e) {
            }
            return {
                up: false,
                latency_ms,
                raw_data: { headers, responseStatus, textResponse }
            };
        }
        return {
            timestamp: (new Date()).toISOString(),
            up: true,
            latency_ms,
            raw_data: { headers, responseStatus }
        };
    })).catch((error) => {
        console.log(error);
        return {
            timestamp: (new Date()).toISOString(),
            up: false,
            latency_ms: latency_ms,
            raw_data: { headers, responseStatus }
        };
    });
};
const getStations = () => {
    const options = {
        method: 'POST',
        url: env_1.PROJECT_ENV.GRAPHQL_ENDPOINT_URI,
        headers: {
            'content-type': 'application/json',
            'x-hasura-admin-secret': env_1.PROJECT_ENV.GRAPHQL_ADMIN_SECRET
        },
        data: {
            operationName: 'GetStations',
            query: `query GetStations {
  station {
    id
    title
    stream_url
    station_metadata_fetches {
      station_metadata_fetch_category {
        slug
      }
      url
    }
  }
}`,
            variables: {}
        }
    };
    return axios_1.default.request(options).then(function (response) {
        if (!response.data) {
            throw new Error(`Invalid response: ${JSON.stringify(response)}`);
        }
        return response.data.station;
    });
};
const getStationNowPlaying = ({ station }) => __awaiter(void 0, void 0, void 0, function* () {
    // TODO: in the future we might need to combine the output from multiple sources..
    for (let i = 0; i < station.station_metadata_fetches.length; i++) {
        const stationMetadataFetcher = station.station_metadata_fetches[i];
        if (stationMetadataFetcher.station_metadata_fetch_category.slug === "shoutcast") {
            return extractShoutcastNowPlaying({ shoutcast_stats_url: stationMetadataFetcher.url });
        }
        if (stationMetadataFetcher.station_metadata_fetch_category.slug === "radio_co") {
            return extractRadioCoNowPlaying({ radio_co_stats_url: stationMetadataFetcher.url });
        }
        if (stationMetadataFetcher.station_metadata_fetch_category.slug === "icecast") {
            return extractIcecastNowPlaying({ icecast_stats_url: stationMetadataFetcher.url });
        }
        if (stationMetadataFetcher.station_metadata_fetch_category.slug === "shoutcast_xml") {
            return extractShoutcastXmlNowPlaying({ shoutcast_xml_stats_url: stationMetadataFetcher.url });
        }
        if (stationMetadataFetcher.station_metadata_fetch_category.slug === "old_icecast_html") {
            return extractOldIcecastHtmlNowPlaying({ old_icecast_html_stats_url: stationMetadataFetcher.url });
        }
        if (stationMetadataFetcher.station_metadata_fetch_category.slug === "old_shoutcast_html") {
            return extractOldShoutcastHtmlNowPlaying({ old_shoutcast_stats_html_url: stationMetadataFetcher.url });
        }
        return {
            timestamp: (new Date()).toISOString(),
            current_song: null,
            listeners: null,
            raw_data: {},
            error: null
        };
    }
});
const updateStationMetadata = ({ station, stationNowPlaying, stationUptime }) => __awaiter(void 0, void 0, void 0, function* () {
    const options = {
        method: 'POST',
        url: env_1.PROJECT_ENV.GRAPHQL_ENDPOINT_URI,
        headers: {
            'content-type': 'application/json',
            'x-hasura-admin-secret': env_1.PROJECT_ENV.GRAPHQL_ADMIN_SECRET
        },
        data: {
            operationName: 'UpdateStationMetadata',
            query: `mutation UpdateStationMetadata {
  insert_station_now_playing_one(
    object: {
      station_id: ${station.id}
      timestamp: "${stationNowPlaying.timestamp}"
      song: { 
        data: { name: "${stationNowPlaying.current_song.name}", artist: "${stationNowPlaying.current_song.artist}" } 
        on_conflict: {
          constraint: song_name_artist_key
          update_columns: updated_at
        }
      }
      listeners: ${stationNowPlaying.listeners}
      raw_data: "${JSON.stringify(stationNowPlaying.raw_data)}"
      error: "${JSON.stringify(stationNowPlaying.error)}"
    }
  ) {
    id
  }
  insert_station_uptime_one(
    object: { station_id: ${station.id}, timestamp: "${stationUptime.timestamp}", is_up: ${stationUptime.is_up}, latency_ms: ${stationUptime.latency_ms}, raw_data: "${JSON.stringify(stationUptime.raw_data)}" }
  ) {
    id
  }
}
`,
            variables: {}
        }
    };
    return axios_1.default.request(options).then(function (response) {
        if (!response.data) {
            throw new Error(`Invalid response: ${JSON.stringify(response)}`);
        }
        return typeof response.data.insert_station_now_playing_one.id !== "undefined" && typeof response.data.insert_station_uptime_one.id !== "undefined";
    });
});
const refreshStationsMetadata = () => __awaiter(void 0, void 0, void 0, function* () {
    const stations = yield getStations();
    yield bluebird_1.Promise.map(stations, (station) => __awaiter(void 0, void 0, void 0, function* () {
        const stationNowPlaying = yield getStationNowPlaying({ station });
        const stationUptime = yield getStationUptime({ station });
        yield updateStationMetadata({ station, stationNowPlaying, stationUptime });
    }), {
        concurrency: 30,
    });
    return true;
});
exports.refreshStationsMetadata = refreshStationsMetadata;
