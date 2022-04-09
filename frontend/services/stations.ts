import axios, { AxiosRequestConfig } from "axios";
import { StationsMetadata } from "../types";
import { PROJECT_ENV } from "../utils/env";

export const getStationsMetadata = (): Promise<StationsMetadata> => {
  const options: AxiosRequestConfig = {
    method: "POST",
    url: PROJECT_ENV.FRONTEND_GRAPHQL_ENDPOINT_URI,
    headers: {
      "content-type": "application/json",
    },
    data: {
      operationName: "GetStations",
      query: `
query GetStations {
  station_groups {
    id
    name
    order
    station_to_station_groups {
      station_id
    }
  }
  stations {
    id
    order
    title
    website
    email
    stream_url
    thumbnail_url
    uptime {
      is_up
      latency_ms
      timestamp
    }
    now_playing {
      id
      timestamp
      listeners
      song {
        id
        name
        thumbnail_url
        artist {
          id
          name
          thumbnail_url
        }
      }
    }
  }
}
    `,
      variables: {},
    },
  };

  // const data = {
  //   "data": {
  //     "station_groups": [
  //       {
  //         "id": 1,
  //         "name": "General",
  //         "order": 1,
  //         "station_to_station_groups": [
  //           {
  //             "station_id": 0
  //           },
  //           {
  //             "station_id": 6
  //           },
  //           {
  //             "station_id": 7
  //           },
  //           {
  //             "station_id": 11
  //           },
  //           {
  //             "station_id": 21
  //           },
  //           {
  //             "station_id": 25
  //           },
  //           {
  //             "station_id": 26
  //           },
  //           {
  //             "station_id": 27
  //           },
  //           {
  //             "station_id": 28
  //           }
  //         ]
  //       },
  //       {
  //         "id": 2,
  //         "name": "Muzica",
  //         "order": 2,
  //         "station_to_station_groups": [
  //           {
  //             "station_id": 0
  //           },
  //           {
  //             "station_id": 6
  //           },
  //           {
  //             "station_id": 7
  //           },
  //           {
  //             "station_id": 10
  //           },
  //           {
  //             "station_id": 11
  //           },
  //           {
  //             "station_id": 12
  //           },
  //           {
  //             "station_id": 13
  //           },
  //           {
  //             "station_id": 14
  //           },
  //           {
  //             "station_id": 17
  //           },
  //           {
  //             "station_id": 18
  //           },
  //           {
  //             "station_id": 19
  //           },
  //           {
  //             "station_id": 20
  //           },
  //           {
  //             "station_id": 21
  //           },
  //           {
  //             "station_id": 24
  //           },
  //           {
  //             "station_id": 25
  //           },
  //           {
  //             "station_id": 26
  //           },
  //           {
  //             "station_id": 27
  //           },
  //           {
  //             "station_id": 28
  //           },
  //           {
  //             "station_id": 9
  //           }
  //         ]
  //       },
  //       {
  //         "id": 3,
  //         "name": "Popular",
  //         "order": 3,
  //         "station_to_station_groups": [
  //           {
  //             "station_id": 2
  //           },
  //           {
  //             "station_id": 18
  //           },
  //           {
  //             "station_id": 19
  //           },
  //           {
  //             "station_id": 21
  //           },
  //           {
  //             "station_id": 24
  //           }
  //         ]
  //       },
  //       {
  //         "id": 4,
  //         "name": "Predici",
  //         "order": 4,
  //         "station_to_station_groups": [
  //           {
  //             "station_id": 1
  //           },
  //           {
  //             "station_id": 25
  //           }
  //         ]
  //       },
  //       {
  //         "id": 5,
  //         "name": "Worship",
  //         "order": 5,
  //         "station_to_station_groups": [
  //           {
  //             "station_id": 3
  //           },
  //           {
  //             "station_id": 10
  //           },
  //           {
  //             "station_id": 16
  //           },
  //           {
  //             "station_id": 17
  //           },
  //           {
  //             "station_id": 20
  //           }
  //         ]
  //       },
  //       {
  //         "id": 6,
  //         "name": "International",
  //         "order": 6,
  //         "station_to_station_groups": [
  //           {
  //             "station_id": 4
  //           },
  //           {
  //             "station_id": 22
  //           },
  //           {
  //             "station_id": 23
  //           }
  //         ]
  //       },
  //       {
  //         "id": 7,
  //         "name": "Gospel",
  //         "order": 7,
  //         "station_to_station_groups": [
  //           {
  //             "station_id": 23
  //           }
  //         ]
  //       },
  //       {
  //         "id": 8,
  //         "name": "Instrumental",
  //         "order": 8,
  //         "station_to_station_groups": [
  //           {
  //             "station_id": 5
  //           }
  //         ]
  //       },
  //       {
  //         "id": 9,
  //         "name": "Emisiuni",
  //         "order": 3.1,
  //         "station_to_station_groups": [
  //           {
  //             "station_id": 6
  //           },
  //           {
  //             "station_id": 7
  //           },
  //           {
  //             "station_id": 11
  //           },
  //           {
  //             "station_id": 21
  //           },
  //           {
  //             "station_id": 26
  //           }
  //         ]
  //       },
  //       {
  //         "id": 10,
  //         "name": "Biblia",
  //         "order": 9,
  //         "station_to_station_groups": [
  //           {
  //             "station_id": 8
  //           }
  //         ]
  //       },
  //       {
  //         "id": 11,
  //         "name": "Copii",
  //         "order": 9,
  //         "station_to_station_groups": [
  //           {
  //             "station_id": 15
  //           }
  //         ]
  //       }
  //     ],
  //     "stations": [
  //       {
  //         "id": 22,
  //         "order": 22,
  //         "title": "Radio Moody Chicago",
  //         "website": "https://www.moodyradio.org/stations/chicago/",
  //         "email": "wmbi@moody.edu",
  //         "stream_url": "https://primary.moodyradiostream.org/wrmb-high.aac",
  //         "thumbnail_url": "",
  //         "uptime": {
  //           "is_up": true,
  //           "latency_ms": 576,
  //           "timestamp": "2022-04-02T11:39:33.296+00:00"
  //         },
  //         "now_playing": {
  //           "id": 7732,
  //           "timestamp": "2022-04-02T11:39:30.693+00:00",
  //           "listeners": null,
  //           "song": {
  //             "id": 1,
  //             "name": "undefined",
  //             "artist": "undefined"
  //           }
  //         }
  //       },
  //       {
  //         "id": 16,
  //         "order": 16,
  //         "title": "Radio Elim Plus",
  //         "website": "https://www.radioelim.ro/",
  //         "email": "contact@radioelim.ro",
  //         "stream_url": "http://91.213.11.102:8003/stream",
  //         "thumbnail_url": "",
  //         "uptime": {
  //           "is_up": true,
  //           "latency_ms": 36,
  //           "timestamp": "2022-04-02T11:39:30.848+00:00"
  //         },
  //         "now_playing": {
  //           "id": 7716,
  //           "timestamp": "2022-04-02T11:39:30.812+00:00",
  //           "listeners": 3,
  //           "song": {
  //             "id": 7708,
  //             "name": "Let The Redeemed",
  //             "artist": "Danny Daniels"
  //           }
  //         }
  //       },
  //       {
  //         "id": 13,
  //         "order": 13,
  //         "title": "Radio Elim Air",
  //         "website": "https://www.radioelim.ro/",
  //         "email": "contact@radioelim.ro",
  //         "stream_url": "http://91.213.11.102:8011/stream",
  //         "thumbnail_url": "",
  //         "uptime": {
  //           "is_up": true,
  //           "latency_ms": 35,
  //           "timestamp": "2022-04-02T11:39:30.849+00:00"
  //         },
  //         "now_playing": {
  //           "id": 7717,
  //           "timestamp": "2022-04-02T11:39:30.814+00:00",
  //           "listeners": 2,
  //           "song": {
  //             "id": 7709,
  //             "name": "Trading My Sorrows",
  //             "artist": "Sam Levine"
  //           }
  //         }
  //       },
  //       {
  //         "id": 9,
  //         "order": 9,
  //         "title": "Radio Biruitor",
  //         "website": "https://biruitor.eu/",
  //         "email": "radio@biruitor.eu",
  //         "stream_url": "https://cast1.asurahosting.com/proxy/valer/stream",
  //         "thumbnail_url": "",
  //         "uptime": {
  //           "is_up": true,
  //           "latency_ms": 361,
  //           "timestamp": "2022-04-02T11:23:12.843+00:00"
  //         },
  //         "now_playing": {
  //           "id": 7701,
  //           "timestamp": "2022-04-02T11:23:11.482+00:00",
  //           "listeners": 5,
  //           "song": {
  //             "id": 7458,
  //             "name": "Speranta si Puiu Chibici",
  //             "artist": "Intoarce-te din drumul tau"
  //           }
  //         }
  //       },
  //       {
  //         "id": 5,
  //         "order": 5,
  //         "title": "Aripi Spre Cer Instrumental",
  //         "website": "https://aripisprecer.ro",
  //         "email": "contact@aripisprecer.ro",
  //         "stream_url": "https://instrumental.stream.aripisprecer.ro/radio.mp3;",
  //         "thumbnail_url": "",
  //         "uptime": {
  //           "is_up": true,
  //           "latency_ms": 26,
  //           "timestamp": "2022-04-02T11:39:31.919+00:00"
  //         },
  //         "now_playing": {
  //           "id": 7719,
  //           "timestamp": "2022-04-02T11:39:30.893+00:00",
  //           "listeners": 12,
  //           "song": {
  //             "id": 7717,
  //             "name": "I'll Go Where You Want Me to Go",
  //             "artist": "Joe Gransden"
  //           }
  //         }
  //       },
  //       {
  //         "id": 11,
  //         "order": 11,
  //         "title": "Radio de Cuvant",
  //         "website": "https://radiodecuvant.ro/",
  //         "email": "radiodecuvant@gmail.com",
  //         "stream_url": "https://streamer.radio.co/sb94ce6fe2/listen",
  //         "thumbnail_url": "",
  //         "uptime": {
  //           "is_up": false,
  //           "latency_ms": -1,
  //           "timestamp": "2022-04-02T11:23:21.055+00:00"
  //         },
  //         "now_playing": {
  //           "id": 7706,
  //           "timestamp": "2022-04-02T11:23:11.449+00:00",
  //           "listeners": null,
  //           "song": {
  //             "id": 7645,
  //             "name": "Eclesiastul ",
  //             "artist": "SUNNY"
  //           }
  //         }
  //       },
  //       {
  //         "id": 20,
  //         "order": 20,
  //         "title": "Radio Levi",
  //         "website": "https://radiolevi.ro/",
  //         "email": "radiolevionline@gmail.com",
  //         "stream_url": "https://audio-radioleviro.bisericilive.com/radioleviro.mp3",
  //         "thumbnail_url": "",
  //         "uptime": {
  //           "is_up": true,
  //           "latency_ms": 164,
  //           "timestamp": "2022-04-02T11:39:32.101+00:00"
  //         },
  //         "now_playing": {
  //           "id": 7721,
  //           "timestamp": "2022-04-02T11:39:30.937+00:00",
  //           "listeners": 80,
  //           "song": {
  //             "id": 7719,
  //             "name": "Suflet luat de valuri",
  //             "artist": "Echipa GECMC"
  //           }
  //         }
  //       },
  //       {
  //         "id": 7,
  //         "order": 7,
  //         "title": "Radio Armonia",
  //         "website": "https://www.radioarmonia.ro/",
  //         "email": "office@radioarmonia.ro",
  //         "stream_url": "http://video.bluespot.ro:8001/listen.mp3",
  //         "thumbnail_url": "",
  //         "uptime": {
  //           "is_up": true,
  //           "latency_ms": 231,
  //           "timestamp": "2022-04-02T11:39:32.121+00:00"
  //         },
  //         "now_playing": {
  //           "id": 7723,
  //           "timestamp": "2022-04-02T11:39:30.889+00:00",
  //           "listeners": 4,
  //           "song": {
  //             "id": 7721,
  //             "name": "Glas de slava",
  //             "artist": "Stefana Delia Paduraru"
  //           }
  //         }
  //       },
  //       {
  //         "id": 1,
  //         "order": 1,
  //         "title": "Aripi Spre Cer Predici",
  //         "website": "https://aripisprecer.ro",
  //         "email": "contact@aripisprecer.ro",
  //         "stream_url": "https://predici.stream.aripisprecer.ro/radio.mp3;",
  //         "thumbnail_url": "",
  //         "uptime": {
  //           "is_up": true,
  //           "latency_ms": 396,
  //           "timestamp": "2022-04-02T11:39:33.293+00:00"
  //         },
  //         "now_playing": {
  //           "id": 7724,
  //           "timestamp": "2022-04-02T11:39:30.896+00:00",
  //           "listeners": 37,
  //           "song": {
  //             "id": 7724,
  //             "name": "Ce-ar fi faptura-mi fara Tine",
  //             "artist": "Iudita Paval"
  //           }
  //         }
  //       },
  //       {
  //         "id": 3,
  //         "order": 3,
  //         "title": "Aripi Spre Cer Worship",
  //         "website": "https://aripisprecer.ro",
  //         "email": "contact@aripisprecer.ro",
  //         "stream_url": "https://worship.stream.aripisprecer.ro/radio.mp3;",
  //         "thumbnail_url": "",
  //         "uptime": {
  //           "is_up": true,
  //           "latency_ms": 394,
  //           "timestamp": "2022-04-02T11:39:33.293+00:00"
  //         },
  //         "now_playing": {
  //           "id": 7725,
  //           "timestamp": "2022-04-02T11:39:30.898+00:00",
  //           "listeners": 14,
  //           "song": {
  //             "id": 7722,
  //             "name": "Tu esti",
  //             "artist": "Chris"
  //           }
  //         }
  //       },
  //       {
  //         "id": 19,
  //         "order": 19,
  //         "title": "Radio Iubire Fara Margini",
  //         "website": "https://radioiubire.ucoz.net/",
  //         "email": "",
  //         "stream_url": "https/ssl.omegahost.ro/7043/stream",
  //         "thumbnail_url": "",
  //         "uptime": {
  //           "is_up": false,
  //           "latency_ms": -1,
  //           "timestamp": "2022-04-02T11:22:36.929+00:00"
  //         },
  //         "now_playing": {
  //           "id": 7678,
  //           "timestamp": "2022-04-02T11:22:33.716+00:00",
  //           "listeners": 4,
  //           "song": {
  //             "id": 7639,
  //             "name": "Muzica Crestina Live ",
  //             "artist": "Fratii DINESCU"
  //           }
  //         }
  //       },
  //       {
  //         "id": 4,
  //         "order": 4,
  //         "title": "Aripi Spre Cer International",
  //         "website": "https://aripisprecer.ro",
  //         "email": "contact@aripisprecer.ro",
  //         "stream_url": "https://international.stream.aripisprecer.ro/radio.mp3;",
  //         "thumbnail_url": "",
  //         "uptime": {
  //           "is_up": true,
  //           "latency_ms": 21,
  //           "timestamp": "2022-04-02T11:39:31.916+00:00"
  //         },
  //         "now_playing": {
  //           "id": 7728,
  //           "timestamp": "2022-04-02T11:39:30.894+00:00",
  //           "listeners": 11,
  //           "song": {
  //             "id": 7726,
  //             "name": "I Surrender All All To Jesus",
  //             "artist": "Casting Crowns"
  //           }
  //         }
  //       },
  //       {
  //         "id": 23,
  //         "order": 23,
  //         "title": "Radio Old Christian Radio",
  //         "website": "https://www.oldchristianradio.com/",
  //         "email": "mcfaddenm99@yahoo.com",
  //         "stream_url": "https://stream.radio.co/sf2c714555/listen",
  //         "thumbnail_url": "",
  //         "uptime": {
  //           "is_up": false,
  //           "latency_ms": -1,
  //           "timestamp": "2022-04-02T11:22:39.117+00:00"
  //         },
  //         "now_playing": {
  //           "id": 7680,
  //           "timestamp": "2022-04-02T11:22:32.395+00:00",
  //           "listeners": null,
  //           "song": {
  //             "id": 7560,
  //             "name": "I Am His And He Is Mine",
  //             "artist": "Anna Mieczkowski"
  //           }
  //         }
  //       },
  //       {
  //         "id": 14,
  //         "order": 14,
  //         "title": "Radio Elim Christmas",
  //         "website": "https://www.radioelim.ro/",
  //         "email": "contact@radioelim.ro",
  //         "stream_url": "http://91.213.11.102:8015/stream",
  //         "thumbnail_url": "",
  //         "uptime": {
  //           "is_up": false,
  //           "latency_ms": -1,
  //           "timestamp": "2022-04-02T11:39:30.811+00:00"
  //         },
  //         "now_playing": {
  //           "id": 7714,
  //           "timestamp": "2022-04-02T11:39:30.758+00:00",
  //           "listeners": null,
  //           "song": {
  //             "id": 1,
  //             "name": "undefined",
  //             "artist": "undefined"
  //           }
  //         }
  //       },
  //       {
  //         "id": 10,
  //         "order": 10,
  //         "title": "Radio Ciresarii",
  //         "website": "https://ciresarii.ro/",
  //         "email": "head.office@ciresarii.ro",
  //         "stream_url": "https://s3.radio.co/s6c0a773ad/listen",
  //         "thumbnail_url": "",
  //         "uptime": {
  //           "is_up": false,
  //           "latency_ms": -1,
  //           "timestamp": "2022-04-02T11:22:40.122+00:00"
  //         },
  //         "now_playing": {
  //           "id": 7681,
  //           "timestamp": "2022-04-02T11:22:32.405+00:00",
  //           "listeners": null,
  //           "song": {
  //             "id": 7561,
  //             "name": "Difference Maker",
  //             "artist": "NEEDTOBREATHE"
  //           }
  //         }
  //       },
  //       {
  //         "id": 12,
  //         "order": 12,
  //         "title": "Radio Ekklesia",
  //         "website": "https://radioekklesia.com/",
  //         "email": "",
  //         "stream_url": "http://asculta.radioekklesia.com:8005/stream",
  //         "thumbnail_url": "",
  //         "uptime": {
  //           "is_up": true,
  //           "latency_ms": 398,
  //           "timestamp": "2022-04-02T11:39:33.291+00:00"
  //         },
  //         "now_playing": {
  //           "id": 7731,
  //           "timestamp": "2022-04-02T11:39:30.893+00:00",
  //           "listeners": 127,
  //           "song": {
  //             "id": 7729,
  //             "name": "",
  //             "artist": "Tabita Alexa"
  //           }
  //         }
  //       },
  //       {
  //         "id": 15,
  //         "order": 15,
  //         "title": "Radio Elim Kids",
  //         "website": "https://www.radioelim.ro/",
  //         "email": "contact@radioelim.ro",
  //         "stream_url": "http://91.213.11.102:8007/stream",
  //         "thumbnail_url": "",
  //         "uptime": {
  //           "is_up": true,
  //           "latency_ms": 74,
  //           "timestamp": "2022-04-02T11:39:30.833+00:00"
  //         },
  //         "now_playing": {
  //           "id": 7715,
  //           "timestamp": "2022-04-02T11:39:30.759+00:00",
  //           "listeners": 1,
  //           "song": {
  //             "id": 7707,
  //             "name": "Trust & Obey",
  //             "artist": "Hillsong Kids"
  //           }
  //         }
  //       },
  //       {
  //         "id": 21,
  //         "order": 21,
  //         "title": "Radio Micul Samaritean",
  //         "website": "https://www.miculsamaritean.com/",
  //         "email": "miculsamariteanmd@yahoo.com",
  //         "stream_url": "https://s5.radio.co/sfff7b7e97/listen",
  //         "thumbnail_url": "",
  //         "uptime": {
  //           "is_up": false,
  //           "latency_ms": -1,
  //           "timestamp": "2022-04-02T11:22:40.697+00:00"
  //         },
  //         "now_playing": {
  //           "id": 7682,
  //           "timestamp": "2022-04-02T11:22:33.718+00:00",
  //           "listeners": null,
  //           "song": {
  //             "id": 1,
  //             "name": "undefined",
  //             "artist": "undefined"
  //           }
  //         }
  //       },
  //       {
  //         "id": 6,
  //         "order": 6,
  //         "title": "Radio ALT FM Arad",
  //         "website": "https://www.altfm.ro",
  //         "email": "office@altfm.ro",
  //         "stream_url": "http://asculta.radiocnm.ro:8002/live",
  //         "thumbnail_url": "",
  //         "uptime": {
  //           "is_up": true,
  //           "latency_ms": 362,
  //           "timestamp": "2022-04-02T11:39:33.294+00:00"
  //         },
  //         "now_playing": {
  //           "id": 7733,
  //           "timestamp": "2022-04-02T11:39:30.932+00:00",
  //           "listeners": 22,
  //           "song": {
  //             "id": 202,
  //             "name": "",
  //             "artist": ""
  //           }
  //         }
  //       },
  //       {
  //         "id": 24,
  //         "order": 24,
  //         "title": "Radio O Noua Sansa",
  //         "website": "https://radioonouasansa.ro/radio/",
  //         "email": "",
  //         "stream_url": "https://securestreams5.autopo.st:1951/;?type=http&nocache=15",
  //         "thumbnail_url": "",
  //         "uptime": {
  //           "is_up": true,
  //           "latency_ms": 402,
  //           "timestamp": "2022-04-02T11:23:12.847+00:00"
  //         },
  //         "now_playing": {
  //           "id": 7699,
  //           "timestamp": "2022-04-02T11:23:11.444+00:00",
  //           "listeners": 8,
  //           "song": {
  //             "id": 7513,
  //             "name": "Ierusalim",
  //             "artist": "Ionut Gontaru"
  //           }
  //         }
  //       },
  //       {
  //         "id": 18,
  //         "order": 18,
  //         "title": "Radio Gosen",
  //         "website": "https://filadelfia.md/",
  //         "email": "info@filadelfia.md",
  //         "stream_url": "https://sp.totalstreaming.net/8125/stream",
  //         "thumbnail_url": "",
  //         "uptime": {
  //           "is_up": true,
  //           "latency_ms": 413,
  //           "timestamp": "2022-04-02T11:23:12.844+00:00"
  //         },
  //         "now_playing": {
  //           "id": 7702,
  //           "timestamp": "2022-04-02T11:23:11.431+00:00",
  //           "listeners": 350,
  //           "song": {
  //             "id": 7642,
  //             "name": "Gabi Ilut-Ca Cerbul Dupa Ape",
  //             "artist": ""
  //           }
  //         }
  //       },
  //       {
  //         "id": 27,
  //         "order": 27,
  //         "title": "Radio Vocea Evangheliei Cluj",
  //         "website": "https://rvecj.ro/",
  //         "email": "rvecluj@gmail.com",
  //         "stream_url": "http://89.36.154.3:8000/;",
  //         "thumbnail_url": "",
  //         "uptime": {
  //           "is_up": false,
  //           "latency_ms": -1,
  //           "timestamp": "2022-04-02T07:50:31.428+00:00"
  //         },
  //         "now_playing": {
  //           "id": 306,
  //           "timestamp": "2022-04-02T07:50:20.744+00:00",
  //           "listeners": null,
  //           "song": {
  //             "id": 1,
  //             "name": "undefined",
  //             "artist": "undefined"
  //           }
  //         }
  //       },
  //       {
  //         "id": 26,
  //         "order": 26,
  //         "title": "Radio Vocea Evangheliei Bucuresti",
  //         "website": "https://rvebucuresti.ro/",
  //         "email": "contact@rvebucuresti.ro",
  //         "stream_url": "https://lb01.bpstream.com:8618/stream",
  //         "thumbnail_url": "",
  //         "uptime": {
  //           "is_up": true,
  //           "latency_ms": 72,
  //           "timestamp": "2022-04-02T11:39:30.923+00:00"
  //         },
  //         "now_playing": {
  //           "id": 7718,
  //           "timestamp": "2022-04-02T11:39:30.851+00:00",
  //           "listeners": 28,
  //           "song": {
  //             "id": 7350,
  //             "name": "Cand Domnul porunceste",
  //             "artist": "Grup Eldad"
  //           }
  //         }
  //       },
  //       {
  //         "id": 17,
  //         "order": 17,
  //         "title": "Radio Filadelfia",
  //         "website": "https://www.radiofiladelfia.ro/",
  //         "email": "redactie@radiofiladelfia.ro",
  //         "stream_url": "https://asculta.radiofiladelfia.ro:8000/;",
  //         "thumbnail_url": "",
  //         "uptime": {
  //           "is_up": true,
  //           "latency_ms": 106,
  //           "timestamp": "2022-04-02T11:39:31.927+00:00"
  //         },
  //         "now_playing": {
  //           "id": 7720,
  //           "timestamp": "2022-04-02T11:39:30.821+00:00",
  //           "listeners": 4,
  //           "song": {
  //             "id": 7711,
  //             "name": "Speranta Mea",
  //             "artist": "Teo Family"
  //           }
  //         }
  //       },
  //       {
  //         "id": 28,
  //         "order": 28,
  //         "title": "Radio Vocea Evangheliei Constanta",
  //         "website": "http://rvect.ro",
  //         "email": "contact@rvect.ro",
  //         "stream_url": "https://audio-rvectro.bisericilive.com/rvectro.mp3",
  //         "thumbnail_url": "",
  //         "uptime": {
  //           "is_up": true,
  //           "latency_ms": 195,
  //           "timestamp": "2022-04-02T11:39:32.109+00:00"
  //         },
  //         "now_playing": {
  //           "id": 7722,
  //           "timestamp": "2022-04-02T11:39:31.914+00:00",
  //           "listeners": 3,
  //           "song": {
  //             "id": 7720,
  //             "name": "Wondrous Love feat Kari Jobe",
  //             "artist": "Aaron Shust"
  //           }
  //         }
  //       },
  //       {
  //         "id": 8,
  //         "order": 8,
  //         "title": "Radio Biblia Online",
  //         "website": "http://ascultabiblia.blogspot.com",
  //         "email": "",
  //         "stream_url": "http://209.95.50.189:8006/",
  //         "thumbnail_url": "",
  //         "uptime": {
  //           "is_up": false,
  //           "latency_ms": -1,
  //           "timestamp": "2022-04-02T11:39:33.29+00:00"
  //         },
  //         "now_playing": {
  //           "id": 7726,
  //           "timestamp": "2022-04-02T11:39:31.9+00:00",
  //           "listeners": null,
  //           "song": {
  //             "id": 1,
  //             "name": "undefined",
  //             "artist": "undefined"
  //           }
  //         }
  //       },
  //       {
  //         "id": 25,
  //         "order": 25,
  //         "title": "Radio Philadelphia Mansuè",
  //         "website": "http://www.philadelphiamansue.it/radio-philadelphia/",
  //         "email": "",
  //         "stream_url": "http://94.130.106.91/radio/8000/radio.mp3",
  //         "thumbnail_url": "",
  //         "uptime": {
  //           "is_up": true,
  //           "latency_ms": 113,
  //           "timestamp": "2022-04-02T11:39:30.834+00:00"
  //         },
  //         "now_playing": {
  //           "id": 7727,
  //           "timestamp": "2022-04-02T11:39:30.697+00:00",
  //           "listeners": null,
  //           "song": {
  //             "id": 1,
  //             "name": "undefined",
  //             "artist": "undefined"
  //           }
  //         }
  //       },
  //       {
  //         "id": 2,
  //         "order": 2,
  //         "title": "Aripi Spre Cer Popular",
  //         "website": "https://aripisprecer.ro",
  //         "email": "contact@aripisprecer.ro",
  //         "stream_url": "https://popular.stream.aripisprecer.ro/radio.mp3;",
  //         "thumbnail_url": "",
  //         "uptime": {
  //           "is_up": true,
  //           "latency_ms": 373,
  //           "timestamp": "2022-04-02T11:39:33.293+00:00"
  //         },
  //         "now_playing": {
  //           "id": 7730,
  //           "timestamp": "2022-04-02T11:39:30.92+00:00",
  //           "listeners": 73,
  //           "song": {
  //             "id": 7727,
  //             "name": "Singur",
  //             "artist": "Mihaela Verhun"
  //           }
  //         }
  //       },
  //       {
  //         "id": 0,
  //         "order": 0,
  //         "title": "Aripi Spre Cer",
  //         "website": "https://aripisprecer.ro",
  //         "email": "contact@aripisprecer.ro",
  //         "stream_url": "https://mobile.stream.aripisprecer.ro/radio.mp3;",
  //         "thumbnail_url": "",
  //         "uptime": {
  //           "is_up": true,
  //           "latency_ms": 396,
  //           "timestamp": "2022-04-02T11:39:33.294+00:00"
  //         },
  //         "now_playing": {
  //           "id": 7729,
  //           "timestamp": "2022-04-02T11:39:30.897+00:00",
  //           "listeners": 82,
  //           "song": {
  //             "id": 7728,
  //             "name": "Asa-ntr-o liniste si-un har",
  //             "artist": "Miriam Popescu"
  //           }
  //         }
  //       }
  //     ]
  //   }
  // };
  // return new Promise((resolve, reject) => {
  //   return resolve({
  //     station_groups: data.data.station_groups,
  //     stations: data.data.stations,
  //   });
  // })

  return axios.request(options).then(function (response) {
    if (!response.data?.data) {
      throw new Error(`Invalid response: ${JSON.stringify(response.data)}`);
    }

    return {
      station_groups: response.data.data.station_groups,
      stations: response.data.data.stations,
    };
  });
};
