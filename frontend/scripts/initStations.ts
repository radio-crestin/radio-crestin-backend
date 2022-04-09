// import {Station} from "../types";
//
// export const INITIAL_STATIONS: Station[] = [
//   {
//     "id": "1",
//     "order": 1,
//     "title": "Aripi Spre Cer",
//     "website": "https://aripisprecer.ro",
//     "email": "email@aripisprecer.ro",
//     "stream_url": "https://radio.radio-crestin.com/https://mobile.stream.aripisprecer.ro/radio.mp3;",
//     "metadataEndpoint": {
//       "shoutcastStatsUrl": "https://mobile.stream.aripisprecer.ro/stats?json=1",
//     },
//     "thumbnail_url": "/images/default-station-thumbnail.png",
//     "groups": ["General"]
//   },
//   {
//     "id": "2",
//     "order": 2,
//     "title": "Aripi Spre Cer Predici",
//     "website": "https://aripisprecer.ro",
//     "email": "email@aripisprecer.ro",
//     "stream_url": "https://radio.radio-crestin.com/https://predici.stream.aripisprecer.ro/radio.mp3;",
//     "metadataEndpoint": {
//       "shoutcastStatsUrl": "https://predici.stream.aripisprecer.ro/stats?json=1",
//     },
//     "thumbnail_url": "/images/default-station-thumbnail.png",
//     "groups": ["Predici"]
//   },
//   {
//     "id": "3",
//     "order": 3,
//     "title": "Aripi Spre Cer Popular",
//     "website": "https://aripisprecer.ro",
//     "email": "email@aripisprecer.ro",
//     "stream_url": "https://radio.radio-crestin.com/https://popular.stream.aripisprecer.ro/radio.mp3;",
//     "metadataEndpoint": {
//       "shoutcastStatsUrl": "https://popular.stream.aripisprecer.ro/stats?json=1",
//     },
//     "thumbnail_url": "/images/default-station-thumbnail.png",
//     "groups": ["Popular"]
//   },
//   {
//     "id": "4",
//     "order": 4,
//     "title": "Aripi Spre Cer Worship",
//     "website": "https://aripisprecer.ro",
//     "email": "email@aripisprecer.ro",
//     "stream_url": "https://radio.radio-crestin.com/https://worship.stream.aripisprecer.ro/radio.mp3;",
//     "metadataEndpoint": {
//       "shoutcastStatsUrl": "https://worship.stream.aripisprecer.ro/stats?json=1",
//     },
//     "thumbnail_url": "/images/default-station-thumbnail.png",
//     "groups": ["Worship"]
//   },
//   {
//     "id": "5",
//     "order": 5,
//     "title": "Aripi Spre Cer International",
//     "website": "https://aripisprecer.ro",
//     "email": "email@aripisprecer.ro",
//     "stream_url": "https://radio.radio-crestin.com/https://international.stream.aripisprecer.ro/radio.mp3;",
//     "metadataEndpoint": {
//       "shoutcastStatsUrl": "https://international.stream.aripisprecer.ro/stats?json=1",
//     },
//     "thumbnail_url": "/images/default-station-thumbnail.png",
//     "groups": ["International"]
//   },
//   {
//     "id": "6",
//     "order": 6,
//     "title": "Aripi Spre Cer Instrumental",
//     "website": "https://aripisprecer.ro",
//     "email": "email@aripisprecer.ro",
//     "stream_url": "https://radio.radio-crestin.com/https://instrumental.stream.aripisprecer.ro/radio.mp3;",
//     "metadataEndpoint": {
//       "shoutcastStatsUrl": "https://instrumental.stream.aripisprecer.ro/stats?json=1",
//     },
//     "thumbnail_url": "/images/default-station-thumbnail.png",
//     "groups": ["Instrumental"]
//   },
//   // This Station is down
//   // {
//   //     "id": "7",
//   //      "order": 7,
//   //     "title": "Radio ALT FM Arad",
//   //     "website": "https://www.altfm.ro",
//   //     "email": "office@altfm.ro",
//   //     "stream_url": "https://radio.radio-crestin.com/http://asculta.radiocnm.ro:8002/live",
//   //     "oldIcecastHtmlStatsUrl": "http://asculta.radiocnm.ro:8002/",
//   // "thumbnail_url": "/images/default-station-thumbnail.png",
//   // },
//   {
//     "id": "8",
//     "order": 8,
//     "title": "Radio Armonia",
//     "website": "https://www.radioarmonia.ro/",
//     "email": "office@radioarmonia.ro",
//     "stream_url": "https://radio.radio-crestin.com/http://video.bluespot.ro:8001/listen.mp3",
//     "metadataEndpoint": {
//       "shoutcastStatsUrl": "http://video.bluespot.ro:8001/stats?json=1",
//     },
//     "thumbnail_url": "/images/default-station-thumbnail.png",
//     "groups": ["General"]
//   },
//   // TODO: it seems that this stream is not based on the HTTP protocol..
//   // {
//   //   "id": "9",
//   //   "order": 9,
//   //   "title": "Radio Biblia Online",
//   //   "website": "https://ascultabiblia.blogspot.com",
//   //   "email": "",
//   //   "stream_url": "https://radio.radio-crestin.com/http://209.95.50.189:8006/;",
//   //   "oldShoutcastStatsHtmlUrl": "http://209.95.50.189:8006/",
//   //   "thumbnail_url": "/images/default-station-thumbnail.png",
//   //   "groups": ["Biblia"]
//   // },
//   {
//     "id": "10",
//     "order": 10,
//     "title": "Radio Biruitor",
//     "website": "https://biruitor.eu/",
//     "email": "radio@biruitor.eu",
//     "stream_url": "https://radio.radio-crestin.com/https://cast1.asurahosting.com/proxy/valer/stream",
//     "metadataEndpoint": {
//       "icecastStatsUrl": "https://cast1.asurahosting.com/proxy/valer/status-json.xsl?listen_url=live",
//     },
//     "thumbnail_url": "/images/default-station-thumbnail.png",
//     "groups": ["General"]
//   },
//   {
//     "id": "11",
//     "order": 11,
//     "title": "Radio Ciresarii",
//     "website": "https://ciresarii.ro/",
//     "email": "head.office@ciresarii.ro",
//     "stream_url": "https://radio.radio-crestin.com/https://s3.radio.co/s6c0a773ad/listen",
//     "metadataEndpoint": {
//       "radioCoStatsUrl": "https://public.radio.co/stations/s6c0a773ad/status",
//     },
//     "thumbnail_url": "/images/default-station-thumbnail.png",
//     "groups": ["Worship"]
//   },
//   {
//     "id": "12",
//     "order": 12,
//     "title": "Radio de Cuvant",
//     "website": "https://radiodecuvant.ro/",
//     "email": "radiodecuvant@gmail.com",
//     "stream_url": "https://radio.radio-crestin.com/https://streamer.radio.co/sb94ce6fe2/listen",
//     "metadataEndpoint": {
//       "radioCoStatsUrl": "https://public.radio.co/stations/sb94ce6fe2/status",
//     },
//     "thumbnail_url": "/images/default-station-thumbnail.png",
//     "groups": ["General"]
//   },
//   {
//     "id": "13",
//     "order": 13,
//     "title": "Radio Efrata",
//     "website": "https://radioefrata.ro/",
//     "email": "",
//     "stream_url": "https://radio.radio-crestin.com/http://asculta.radioekklesia.com:8005/stream",
//     "metadataEndpoint": {
//       "shoutcastStatsUrl": "http://asculta.radioekklesia.com:8005/stats?json=1",
//     },
//     "thumbnail_url": "/images/default-station-thumbnail.png",
//     "groups": ["General"]
//   },
//   {
//     "id": "14",
//     "order": 14,
//     "title": "Radio Elim Air",
//     "website": "https://www.radioelim.ro/",
//     "email": "email@radioelim.ro",
//     "stream_url": "https://radio.radio-crestin.com/http://91.213.11.102:8011/stream",
//     "metadataEndpoint": {
//       "shoutcastStatsUrl": "http://91.213.11.102:8011/stats?json=1",
//     },
//     "thumbnail_url": "/images/default-station-thumbnail.png",
//     "groups": ["General"]
//   },
//   {
//     "id": "15",
//     "order": 15,
//     "title": "Radio Elim Christmas",
//     "website": "https://www.radioelim.ro/",
//     "email": "email@radioelim.ro",
//     "stream_url": "https://radio.radio-crestin.com/http://91.213.11.102:8015/stream",
//     "metadataEndpoint": {
//       "shoutcastStatsUrl": "http://91.213.11.102:8015/stats?json=1",
//     },
//     "thumbnail_url": "/images/default-station-thumbnail.png",
//     "groups": ["Special"]
//   },
//   {
//     "id": "17",
//     "order": 17,
//     "title": "Radio Elim Kids",
//     "website": "https://www.radioelim.ro/",
//     "email": "email@radioelim.ro",
//     "stream_url": "https://radio.radio-crestin.com/http://91.213.11.102:8007/stream",
//     "metadataEndpoint": {
//       "shoutcastStatsUrl": "http://91.213.11.102:8007/stats?json=1",
//     },
//     "thumbnail_url": "/images/default-station-thumbnail.png",
//     "groups": ["Copii"]
//   },
//   {
//     "id": "18",
//     "order": 18,
//     "title": "Radio Elim Plus",
//     "website": "https://www.radioelim.ro/",
//     "email": "email@radioelim.ro",
//     "stream_url": "https://radio.radio-crestin.com/http://91.213.11.102:8003/stream",
//     "metadataEndpoint": {
//       "shoutcastStatsUrl": "http://91.213.11.102:8003/stats?json=1",
//     },
//     "thumbnail_url": "/images/default-station-thumbnail.png",
//     "groups": ["General"]
//   },
//   {
//     "id": "19",
//     "order": 19,
//     "title": "Radio Filadelfia",
//     "website": "https://www.radiofiladelfia.ro/",
//     "email": "redactie@radiofiladelfia.ro",
//     "stream_url": "https://radio.radio-crestin.com/https://asculta.radiofiladelfia.ro:8000/;",
//     "metadataEndpoint": {
//       "shoutcastStatsUrl": "http://asculta.radiofiladelfia.ro:8080/stats?json=1",
//     },
//     "thumbnail_url": "/images/default-station-thumbnail.png",
//     "groups": ["General"]
//   },
//   {
//     "id": "20",
//     "order": 20,
//     "title": "Radio Gosen",
//     "website": "https://filadelfia.md/",
//     "email": "info@filadelfia.md",
//     "stream_url": "https://sp.totalstreaming.net/8125/stream",
//     "metadataEndpoint": {
//       "shoutcastXmlStatsUrl": "https://sp.totalstreaming.net/8125/stats",
//     },
//     "thumbnail_url": "/images/default-station-thumbnail.png",
//     "groups": ["Popular"]
//   },
//   // This Station is down
//   // {
//   //     "id": "21",
//   //     "order": 21,
//   //     "title": "Radio Iubire Fara Margini",
//   //     "website": "https://radioiubire.ucoz.net/",
//   //     "email": "",
//   //     "stream_url": "https://radio.radio-crestin.com/http://167.114.207.224:7043/;",
//   //     // "oldShoutcastStatsHtmlUrl": "http://167.114.207.224:7043/index.html",
//   // },
//   {
//     "id": "22",
//     "order": 22,
//     "title": "Radio Levi",
//     "website": "https://radiolevi.ro/",
//     "email": "radiolevionline@gmail.com",
//     "stream_url": "https://radio.radio-crestin.com/https://audio-radioleviro.bisericilive.com/radioleviro.mp3",
//     "metadataEndpoint": {
//       "icecastStatsUrl": "https://audio-radioleviro.bisericilive.com/status-json.xsl?listen_url=radioleviro",
//     },
//     "thumbnail_url": "/images/default-station-thumbnail.png",
//     "groups": ["General"]
//   },
//   {
//     "id": "23",
//     "order": 23,
//     "title": "Radio Micul Samaritean",
//     "website": "https://www.miculsamaritean.com/",
//     "email": "miculsamariteanmd@yahoo.com",
//     "stream_url": "https://radio.radio-crestin.com/https://s5.radio.co/sfff7b7e97/listen",
//     "metadataEndpoint": {
//       "radioCoStatsUrl": "https://public.radio.co/stations/sfff7b7e97/status",
//     },
//     "thumbnail_url": "/images/default-station-thumbnail.png",
//     "groups": ["General"]
//   },
//   {
//     "id": "24",
//     "order": 24,
//     "title": "Radio Moody Chicago",
//     "website": "https://www.moodyradio.org/stations/chicago/",
//     "email": "wmbi@moody.edu",
//     "stream_url": "https://radio.radio-crestin.com/https://primary.moodyradiostream.org/wmbifm-high.aac",
//     "metadataEndpoint": {
//       // "icecastStatsUrl": "https://primary.moodyradiostream.org/status-json.xsl?listen_url=wmbifm-high",
//     },
//     "thumbnail_url": "/images/default-station-thumbnail.png",
//     "groups": ["International"]
//   },
//   {
//     "id": "25",
//     "order": 25,
//     "title": "Radio Old Christian Radio",
//     "website": "https://www.oldchristianradio.com/",
//     "email": "mcfaddenm99@yahoo.com",
//     "stream_url": "https://radio.radio-crestin.com/https://stream.radio.co/sf2c714555/listen",
//     "metadataEndpoint": {
//       "radioCoStatsUrl": "https://public.radio.co/stations/sf2c714555/status",
//     },
//     "thumbnail_url": "/images/default-station-thumbnail.png",
//     "groups": ["International"]
//   },
//   {
//     "id": "26",
//     "order": 26,
//     "title": "Radio O Noua Sansa",
//     "website": "https://radioonouasansa.ro/radio/",
//     "email": "",
//     "stream_url": "https://radio.radio-crestin.com/https/securestreams5.autopo.st:1951/;?type=http&nocache=15",
//     "metadataEndpoint": {
//       "shoutcastStatsUrl": "https://securestreams5.autopo.st:1951/stats?json=1",
//     },
//     "thumbnail_url": "/images/default-station-thumbnail.png",
//     "groups": ["General"]
//   },
//   {
//     "id": "27",
//     "order": 27,
//     "title": "Radio Philadelphia Mansuè",
//     "website": "https://www.philadelphiamansue.it/radio-philadelphia/",
//     "email": "",
//     "stream_url": "https://radio.radio-crestin.com/http://94.130.106.91/radio/8000/radio.mp3",
//     "metadataEndpoint": {},
//     "thumbnail_url": "/images/default-station-thumbnail.png",
//     "groups": ["General"]
//   },
//   {
//     "id": "28",
//     "order": 28,
//     "title": "Radio Vocea Evangheliei Bucuresti",
//     "website": "https://rvebucuresti.ro/",
//     "email": "email@rvebucuresti.ro",
//     "stream_url": "https://radio.radio-crestin.com/https/lb01.bpstream.com:8618/;",
//     "metadataEndpoint": {
//       "shoutcastStatsUrl": "https://lb01.bpstream.com:8618/stats?json=1",
//     },
//     "thumbnail_url": "/images/default-station-thumbnail.png",
//     "groups": ["General"]
//   },
//   {
//     "id": "29",
//     "order": 29,
//     "title": "Radio Vocea Evangheliei Cluj",
//     "website": "https://rvecj.ro/",
//     "email": "rvecluj@gmail.com",
//     "stream_url": "https://radio.radio-crestin.com/https/s23.myradiostream.com/:18366/listen.mp3",
//     "metadataEndpoint": {
//       "shoutcastStatsUrl": "https://s23.myradiostream.com/:18366/stats?json=1",
//     },
//     "thumbnail_url": "/images/default-station-thumbnail.png",
//     "groups": ["General"]
//   },
//   {
//     "id": "30",
//     "order": 30,
//     "title": "Radio Vocea Evangheliei Constanta",
//     "website": "https://rvect.ro",
//     "email": "email@rvect.ro",
//     "stream_url": "https://radio.radio-crestin.com/https://audio-rvectro.bisericilive.com/rvectro.mp3",
//     "metadataEndpoint": {
//       "icecastStatsUrl": "https://audio-rvectro.bisericilive.com/status-json.xsl?listen_url=rvectro",
//     },
//     "thumbnail_url": "/images/default-station-thumbnail.png",
//     "groups": ["General"]
//   },
// ];
export const a = {};
