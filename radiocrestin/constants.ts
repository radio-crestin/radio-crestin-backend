import {Station} from "./types";

const defaultStationThumbnail = "/images/default-station-thumbnail.png"

export const STATIONS: Station[] = [
  {
    "id": 1,
    "order": 1,
    "title": "Aripi Spre Cer",
    "website": "https://aripisprecer.ro",
    "contact": "contact@aripisprecer.ro",
    "stream_url": "https://radio.radio-crestin.com/https://mobile.stream.aripisprecer.ro/radio.mp3;",
    "shoutcast_stats_url": "https://mobile.stream.aripisprecer.ro/stats?json=1",
    "thumbnail_url": defaultStationThumbnail,
    "groups": ["General"]
  },
  {
    "id": 2,
    "order": 2,
    "title": "Aripi Spre Cer Predici",
    "website": "https://aripisprecer.ro",
    "contact": "contact@aripisprecer.ro",
    "stream_url": "https://radio.radio-crestin.com/https://predici.stream.aripisprecer.ro/radio.mp3;",
    "shoutcast_stats_url": "https://predici.stream.aripisprecer.ro/stats?json=1",
    "thumbnail_url": defaultStationThumbnail,
    "groups": ["Predici"]
  },
  {
    "id": 3,
    "order": 3,
    "title": "Aripi Spre Cer Popular",
    "website": "https://aripisprecer.ro",
    "contact": "contact@aripisprecer.ro",
    "stream_url": "https://radio.radio-crestin.com/https://popular.stream.aripisprecer.ro/radio.mp3;",
    "shoutcast_stats_url": "https://popular.stream.aripisprecer.ro/stats?json=1",
    "thumbnail_url": defaultStationThumbnail,
    "groups": ["Popular"]
  },
  {
    "id": 4,
    "order": 4,
    "title": "Aripi Spre Cer Worship",
    "website": "https://aripisprecer.ro",
    "contact": "contact@aripisprecer.ro",
    "stream_url": "https://radio.radio-crestin.com/https://worship.stream.aripisprecer.ro/radio.mp3;",
    "shoutcast_stats_url": "https://worship.stream.aripisprecer.ro/stats?json=1",
    "thumbnail_url": defaultStationThumbnail,
    "groups": ["Worship"]
  },
  {
    "id": 5,
    "order": 5,
    "title": "Aripi Spre Cer International",
    "website": "https://aripisprecer.ro",
    "contact": "contact@aripisprecer.ro",
    "stream_url": "https://radio.radio-crestin.com/https://international.stream.aripisprecer.ro/radio.mp3;",
    "shoutcast_stats_url": "https://international.stream.aripisprecer.ro/stats?json=1",
    "thumbnail_url": defaultStationThumbnail,
    "groups": ["International"]
  },
  {
    "id": 6,
    "order": 6,
    "title": "Aripi Spre Cer Instrumental",
    "website": "https://aripisprecer.ro",
    "contact": "contact@aripisprecer.ro",
    "stream_url": "https://radio.radio-crestin.com/https://instrumental.stream.aripisprecer.ro/radio.mp3;",
    "shoutcast_stats_url": "https://instrumental.stream.aripisprecer.ro/stats?json=1",
    "thumbnail_url": defaultStationThumbnail,
    "groups": ["Instrumental"]
  },
  // This Station is down
  // {
  //     "id": 7,
  //      "order": 7,
  //     "title": "Radio ALT FM Arad",
  //     "website": "https://www.altfm.ro",
  //     "contact": "office@altfm.ro",
  //     "stream_url": "https://radio.radio-crestin.com/http://asculta.radiocnm.ro:8002/live",
  //     "old_icecast_html_stats_url": "http://asculta.radiocnm.ro:8002/",
  // "thumbnail_url": defaultStationThumbnail,
  // },
  {
    "id": 8,
    "order": 8,
    "title": "Radio Armonia",
    "website": "https://www.radioarmonia.ro/",
    "contact": "office@radioarmonia.ro",
    "stream_url": "https://radio.radio-crestin.com/http://video.bluespot.ro:8001/listen.mp3",
    "shoutcast_stats_url": "http://video.bluespot.ro:8001/stats?json=1",
    "thumbnail_url": defaultStationThumbnail,
    "groups": ["General"]
  },
  // TODO: it seems that this stream is not based on the HTTP protocol..
  // {
  //   "id": 9,
  //   "order": 9,
  //   "title": "Radio Biblia Online",
  //   "website": "http://ascultabiblia.blogspot.com",
  //   "contact": "",
  //   "stream_url": "https://radio.radio-crestin.com/http://209.95.50.189:8006/;",
  //   "old_shoutcast_stats_html_url": "http://209.95.50.189:8006/",
  //   "thumbnail_url": defaultStationThumbnail,
  //   "groups": ["Biblia"]
  // },
  {
    "id": 10,
    "order": 10,
    "title": "Radio Biruitor",
    "website": "https://biruitor.eu/",
    "contact": "radio@biruitor.eu",
    "stream_url": "https://radio.radio-crestin.com/https://cast1.asurahosting.com/proxy/valer/stream",
    "icecast_stats_url": "https://cast1.asurahosting.com/proxy/valer/status-json.xsl?listen_url=live",
    "thumbnail_url": defaultStationThumbnail,
    "groups": ["General"]
  },
  {
    "id": 11,
    "order": 11,
    "title": "Radio Ciresarii",
    "website": "https://ciresarii.ro/",
    "contact": "head.office@ciresarii.ro",
    "stream_url": "https://radio.radio-crestin.com/https://s3.radio.co/s6c0a773ad/listen",
    "radio_co_stats_url": "https://public.radio.co/stations/s6c0a773ad/status",
    "thumbnail_url": defaultStationThumbnail,
    "groups": ["Worship"]
  },
  {
    "id": 12,
    "order": 12,
    "title": "Radio de Cuvant",
    "website": "https://radiodecuvant.ro/",
    "contact": "radiodecuvant@gmail.com",
    "stream_url": "https://radio.radio-crestin.com/https://streamer.radio.co/sb94ce6fe2/listen",
    "radio_co_stats_url": "https://public.radio.co/stations/sb94ce6fe2/status",
    "thumbnail_url": defaultStationThumbnail,
    "groups": ["General"]
  },
  {
    "id": 13,
    "order": 13,
    "title": "Radio Efrata",
    "website": "https://radioefrata.ro/",
    "contact": "",
    "stream_url": "https://radio.radio-crestin.com/http://asculta.radioekklesia.com:8005/stream",
    "shoutcast_stats_url": "http://asculta.radioekklesia.com:8005/stats?json=1",
    "thumbnail_url": defaultStationThumbnail,
    "groups": ["General"]
  },
  {
    "id": 14,
    "order": 14,
    "title": "Radio Elim Air",
    "website": "https://www.radioelim.ro/",
    "contact": "contact@radioelim.ro",
    "stream_url": "https://radio.radio-crestin.com/http://91.213.11.102:8011/stream",
    "shoutcast_stats_url": "http://91.213.11.102:8011/stats?json=1",
    "thumbnail_url": defaultStationThumbnail,
    "groups": ["General"]
  },
  {
    "id": 15,
    "order": 15,
    "title": "Radio Elim Christmas",
    "website": "https://www.radioelim.ro/",
    "contact": "contact@radioelim.ro",
    "stream_url": "https://radio.radio-crestin.com/http://91.213.11.102:8015/stream",
    "shoutcast_stats_url": "http://91.213.11.102:8015/stats?json=1",
    "thumbnail_url": defaultStationThumbnail,
    "groups": ["Special"]
  },
  {
    "id": 17,
    "order": 17,
    "title": "Radio Elim Kids",
    "website": "https://www.radioelim.ro/",
    "contact": "contact@radioelim.ro",
    "stream_url": "https://radio.radio-crestin.com/http://91.213.11.102:8007/stream",
    "shoutcast_stats_url": "http://91.213.11.102:8007/stats?json=1",
    "thumbnail_url": defaultStationThumbnail,
    "groups": ["Copii"]
  },
  {
    "id": 18,
    "order": 18,
    "title": "Radio Elim Plus",
    "website": "https://www.radioelim.ro/",
    "contact": "contact@radioelim.ro",
    "stream_url": "https://radio.radio-crestin.com/http://91.213.11.102:8003/stream",
    "shoutcast_stats_url": "http://91.213.11.102:8003/stats?json=1",
    "thumbnail_url": defaultStationThumbnail,
    "groups": ["General"]
  },
  {
    "id": 19,
    "order": 19,
    "title": "Radio Filadelfia",
    "website": "https://www.radiofiladelfia.ro/",
    "contact": "redactie@radiofiladelfia.ro",
    "stream_url": "https://radio.radio-crestin.com/https://asculta.radiofiladelfia.ro:8000/;",
    "shoutcast_stats_url": "http://asculta.radiofiladelfia.ro:8080/stats?json=1",
    "thumbnail_url": defaultStationThumbnail,
    "groups": ["General"]
  },
  {
    "id": 20,
    "order": 20,
    "title": "Radio Gosen",
    "website": "https://filadelfia.md/",
    "contact": "info@filadelfia.md",
    "stream_url": "https://sp.totalstreaming.net/8125/stream",
    "shoutcast_xml_stats_url": "https://sp.totalstreaming.net/8125/stats",
    "thumbnail_url": defaultStationThumbnail,
    "groups": ["Popular"]
  },
  // This Station is down
  // {
  //     "id": 21,
  //     "order": 21,
  //     "title": "Radio Iubire Fara Margini",
  //     "website": "https://radioiubire.ucoz.net/",
  //     "contact": "",
  //     "stream_url": "https://radio.radio-crestin.com/http://167.114.207.224:7043/;",
  //     // "old_shoutcast_stats_html_url": "http://167.114.207.224:7043/index.html",
  // },
  {
    "id": 22,
    "order": 22,
    "title": "Radio Levi",
    "website": "https://radiolevi.ro/",
    "contact": "radiolevionline@gmail.com",
    "stream_url": "https://radio.radio-crestin.com/https://audio-radioleviro.bisericilive.com/radioleviro.mp3",
    "icecast_stats_url": "https://audio-radioleviro.bisericilive.com/status-json.xsl?listen_url=radioleviro",
    "thumbnail_url": defaultStationThumbnail,
    "groups": ["General"]
  },
  {
    "id": 23,
    "order": 23,
    "title": "Radio Micul Samaritean",
    "website": "https://www.miculsamaritean.com/",
    "contact": "miculsamariteanmd@yahoo.com",
    "stream_url": "https://radio.radio-crestin.com/https://s5.radio.co/sfff7b7e97/listen",
    "radio_co_stats_url": "https://public.radio.co/stations/sfff7b7e97/status",
    "thumbnail_url": defaultStationThumbnail,
    "groups": ["General"]
  },
  {
    "id": 24,
    "order": 24,
    "title": "Radio Moody Chicago",
    "website": "https://www.moodyradio.org/stations/chicago/",
    "contact": "wmbi@moody.edu",
    "stream_url": "https://radio.radio-crestin.com/https://primary.moodyradiostream.org/wmbifm-high.aac",
    // "icecast_stats_url": "https://primary.moodyradiostream.org/status-json.xsl?listen_url=wmbifm-high",
    "thumbnail_url": defaultStationThumbnail,
    "groups": ["International"]
  },
  {
    "id": 25,
    "order": 25,
    "title": "Radio Old Christian Radio",
    "website": "https://www.oldchristianradio.com/",
    "contact": "mcfaddenm99@yahoo.com",
    "stream_url": "https://radio.radio-crestin.com/https://stream.radio.co/sf2c714555/listen",
    "radio_co_stats_url": "https://public.radio.co/stations/sf2c714555/status",
    "thumbnail_url": defaultStationThumbnail,
    "groups": ["International"]
  },
  {
    "id": 26,
    "order": 26,
    "title": "Radio O Noua Sansa",
    "website": "https://radioonouasansa.ro/radio/",
    "contact": "",
    "stream_url": "https://radio.radio-crestin.com/https/securestreams5.autopo.st:1951/;?type=http&nocache=15",
    "shoutcast_stats_url": "https://securestreams5.autopo.st:1951/stats?json=1",
    "thumbnail_url": defaultStationThumbnail,
    "groups": ["General"]
  },
  {
    "id": 27,
    "order": 27,
    "title": "Radio Philadelphia Mansuè",
    "website": "http://www.philadelphiamansue.it/radio-philadelphia/",
    "contact": "",
    "stream_url": "https://radio.radio-crestin.com/http://94.130.106.91/radio/8000/radio.mp3",
    "thumbnail_url": defaultStationThumbnail,
    "groups": ["General"]
  },
  {
    "id": 28,
    "order": 28,
    "title": "Radio Vocea Evangheliei Bucuresti",
    "website": "https://rvebucuresti.ro/",
    "contact": "contact@rvebucuresti.ro",
    "stream_url": "https://radio.radio-crestin.com/https/lb01.bpstream.com:8618/;",
    "shoutcast_stats_url": "https://lb01.bpstream.com:8618/stats?json=1",
    "thumbnail_url": defaultStationThumbnail,
    "groups": ["General"]
  },
  {
    "id": 29,
    "order": 29,
    "title": "Radio Vocea Evangheliei Cluj",
    "website": "https://rvecj.ro/",
    "contact": "rvecluj@gmail.com",
    "stream_url": "https://radio.radio-crestin.com/https/s23.myradiostream.com/:18366/listen.mp3",
    "shoutcast_stats_url": "https://s23.myradiostream.com/:18366/stats?json=1",
    "thumbnail_url": defaultStationThumbnail,
    "groups": ["General"]
  },
  {
    "id": 30,
    "order": 30,
    "title": "Radio Vocea Evangheliei Constanta",
    "website": "	http://rvect.ro",
    "contact": "contact@rvect.ro",
    "stream_url": "https://radio.radio-crestin.com/https://audio-rvectro.bisericilive.com/rvectro.mp3",
    "icecast_stats_url": "https://audio-rvectro.bisericilive.com/status-json.xsl?listen_url=rvectro",
    "thumbnail_url": defaultStationThumbnail,
    "groups": ["General"]
  },
];
export const HISTORY_DATA_DIRECTORY_PATH = "./public/history"
export const STATIONS_STATS_REFRESH_MS = 15000
