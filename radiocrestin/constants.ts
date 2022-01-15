export interface Station {
    id: number,
    title: string,
    website: string,
    contact: string,
    stream_url: string,

    // Stats urls
    shoutcast_stats_url?: string
    old_icecast_html_stats_url?: string
    icecast_stats_url?: string
    radio_co_stats_url?: string
    shoutcast_xml_stats_url?: string
    old_shoutcast_stats_html_url?: string

}
export const STATIONS:Station[] =   [
    {
        "id": 1,
        "title": "Aripi Spre Cer",
        "website": "https://aripisprecer.ro",
        "contact": "contact@aripisprecer.ro",
        "stream_url": "https://radio.radio-crestin.com/https://mobile.stream.aripisprecer.ro/radio.mp3;",
        "shoutcast_stats_url": "https://mobile.stream.aripisprecer.ro/stats?json=1",
    },
    {
        "id": 2,
        "title": "Aripi Spre Cer Predici",
        "website": "https://aripisprecer.ro",
        "contact": "contact@aripisprecer.ro",
        "stream_url": "https://radio.radio-crestin.com/https://predici.stream.aripisprecer.ro/radio.mp3;",
        "shoutcast_stats_url": "https://predici.stream.aripisprecer.ro/stats?json=1",
    },
    {
        "id": 3,
        "title": "Aripi Spre Cer Popular",
        "website": "https://aripisprecer.ro",
        "contact": "contact@aripisprecer.ro",
        "stream_url": "https://radio.radio-crestin.com/https://popular.stream.aripisprecer.ro/radio.mp3;",
        "shoutcast_stats_url": "https://popular.stream.aripisprecer.ro/stats?json=1",
    },
    {
        "id": 4,
        "title": "Aripi Spre Cer Worship",
        "website": "https://aripisprecer.ro",
        "contact": "contact@aripisprecer.ro",
        "stream_url": "https://radio.radio-crestin.com/https://worship.stream.aripisprecer.ro/radio.mp3;",
        "shoutcast_stats_url": "https://worship.stream.aripisprecer.ro/stats?json=1",
    },
    {
        "id": 5,
        "title": "Aripi Spre Cer International",
        "website": "https://aripisprecer.ro",
        "contact": "contact@aripisprecer.ro",
        "stream_url": "https://radio.radio-crestin.com/https://international.stream.aripisprecer.ro/radio.mp3;",
        "shoutcast_stats_url": "https://international.stream.aripisprecer.ro/stats?json=1",
    },
    {
        "id": 6,
        "title": "Aripi Spre Cer Instrumental",
        "website": "https://aripisprecer.ro",
        "contact": "contact@aripisprecer.ro",
        "stream_url": "https://radio.radio-crestin.com/https://instrumental.stream.aripisprecer.ro/radio.mp3;",
        "shoutcast_stats_url": "https://instrumental.stream.aripisprecer.ro/stats?json=1",
    },
    // This station is down
    // {
    //     "id": 7,
    //     "title": "Radio ALT FM Arad",
    //     "website": "https://www.altfm.ro",
    //     "contact": "office@altfm.ro",
    //     "stream_url": "https://radio.radio-crestin.com/http://asculta.radiocnm.ro:8002/live",
    //     "old_icecast_html_stats_url": "http://asculta.radiocnm.ro:8002/",
    // },
    {
        "id": 8,
        "title": "Radio Armonia",
        "website": "https://www.radioarmonia.ro/",
        "contact": "office@radioarmonia.ro",
        "stream_url": "https://radio.radio-crestin.com/http://video.bluespot.ro:8001/listen.mp3",
        "shoutcast_stats_url": "http://video.bluespot.ro:8001/stats?json=1",
    },
    // TODO: this stream is down
    // {
    //     "id": 9,
    //     "title": "Radio Biblia Online",
    //     "website": "http://ascultabiblia.blogspot.com",
    //     "contact": "",
    //     "stream_url": "https://radio.radio-crestin.com/http://209.95.50.189:8006/;",
    //     // "old_shoutcast_stats_html_url": "https://radio.radio-crestin.com/http://209.95.50.189:8006/index.html",
    // },
    {
        "id": 10,
        "title": "Radio Biruitor",
        "website": "https://biruitor.eu/",
        "contact": "radio@biruitor.eu",
        "stream_url": "https://radio.radio-crestin.com/https://cast1.asurahosting.com/proxy/valer/stream",
        "icecast_stats_url": "https://cast1.asurahosting.com/proxy/valer/status-json.xsl?listen_url=live",
    },
    {
        "id": 11,
        "title": "Radio Ciresarii",
        "website": "https://ciresarii.ro/",
        "contact": "head.office@ciresarii.ro",
        "stream_url": "https://radio.radio-crestin.com/https://s3.radio.co/s6c0a773ad/listen",
        "radio_co_stats_url": "https://public.radio.co/stations/s6c0a773ad/status"
    },
    {
        "id": 12,
        "title": "Radio de Cuvant",
        "website": "https://radiodecuvant.ro/",
        "contact": "radiodecuvant@gmail.com",
        "stream_url": "https://radio.radio-crestin.com/https://streamer.radio.co/sb94ce6fe2/listen",
        "radio_co_stats_url": "https://public.radio.co/stations/sb94ce6fe2/status"
    },
    {
        "id": 13,
        "title": "Radio Efrata",
        "website": "https://radioefrata.ro/",
        "contact": "",
        "stream_url": "https://radio.radio-crestin.com/http://asculta.radioekklesia.com:8005/stream",
        "shoutcast_stats_url": "http://asculta.radioekklesia.com:8005/stats?json=1",
    },
    {
        "id": 14,
        "title": "Radio Elim Air",
        "website": "https://www.radioelim.ro/",
        "contact": "contact@radioelim.ro",
        "stream_url": "https://radio.radio-crestin.com/http://91.213.11.102:8011/stream",
        "shoutcast_stats_url": "http://91.213.11.102:8011/stats?json=1",
    },
    {
        "id": 15,
        "title": "Radio Elim Christmas",
        "website": "https://www.radioelim.ro/",
        "contact": "contact@radioelim.ro",
        "stream_url": "https://radio.radio-crestin.com/http://91.213.11.102:8015/stream",
        "shoutcast_stats_url": "http://91.213.11.102:8015/stats?json=1",
    },
    {
        "id": 17,
        "title": "Radio Elim Kids",
        "website": "https://www.radioelim.ro/",
        "contact": "contact@radioelim.ro",
        "stream_url": "https://radio.radio-crestin.com/http://91.213.11.102:8007/stream",
        "shoutcast_stats_url": "http://91.213.11.102:8007/stats?json=1",
    },
    {
        "id": 18,
        "title": "Radio Elim Plus",
        "website": "https://www.radioelim.ro/",
        "contact": "contact@radioelim.ro",
        "stream_url": "https://radio.radio-crestin.com/http://91.213.11.102:8003/stream",
        "shoutcast_stats_url": "http://91.213.11.102:8003/stats?json=1",
    },
    {
        "id": 19,
        "title": "Radio Filadelfia",
        "website": "https://www.radiofiladelfia.ro/",
        "contact": "redactie@radiofiladelfia.ro",
        "stream_url": "https://radio.radio-crestin.com/https://asculta.radiofiladelfia.ro:8000/;",
        "shoutcast_stats_url": "http://asculta.radiofiladelfia.ro:8080/stats?json=1",
    },
    {
        "id": 20,
        "title": "Radio Gosen",
        "website": "https://filadelfia.md/",
        "contact": "info@filadelfia.md",
        "stream_url": "https://sp.totalstreaming.net/8125/stream",
        "shoutcast_xml_stats_url": "https://sp.totalstreaming.net/8125/stats",
    },
    // This station is down
    // {
    //     "id": 21,
    //     "title": "Radio Iubire Fara Margini",
    //     "website": "https://radioiubire.ucoz.net/",
    //     "contact": "",
    //     "stream_url": "https://radio.radio-crestin.com/http://167.114.207.224:7043/;",
    //     // "old_shoutcast_stats_html_url": "http://167.114.207.224:7043/index.html",
    // },
    {
        "id": 22,
        "title": "Radio Levi",
        "website": "https://radiolevi.ro/",
        "contact": "radiolevionline@gmail.com",
        "stream_url": "https://radio.radio-crestin.com/https://audio-radioleviro.bisericilive.com/radioleviro.mp3",
        "icecast_stats_url": "https://audio-radioleviro.bisericilive.com/status-json.xsl?listen_url=radioleviro",
    },
    {
        "id": 23,
        "title": "Radio Micul Samaritean",
        "website": "https://www.miculsamaritean.com/",
        "contact": "miculsamariteanmd@yahoo.com",
        "stream_url": "https://radio.radio-crestin.com/https://s5.radio.co/sfff7b7e97/listen",
        "radio_co_stats_url": "https://public.radio.co/stations/sfff7b7e97/status"
    },
    {
        "id": 24,
        "title": "Radio Moody Chicago",
        "website": "https://www.moodyradio.org/stations/chicago/",
        "contact": "wmbi@moody.edu",
        "stream_url": "https://radio.radio-crestin.com/https://primary.moodyradiostream.org/wmbifm-high.aac",
        // "icecast_stats_url": "https://primary.moodyradiostream.org/status-json.xsl?listen_url=wmbifm-high",
    },
    {
        "id": 25,
        "title": "Radio Old Christian Radio",
        "website": "https://www.oldchristianradio.com/",
        "contact": "mcfaddenm99@yahoo.com",
        "stream_url": "https://radio.radio-crestin.com/https://stream.radio.co/sf2c714555/listen",
        "radio_co_stats_url": "https://public.radio.co/stations/sf2c714555/status"
    },
    {
        "id": 26,
        "title": "Radio O Noua Sansa",
        "website": "https://radioonouasansa.ro/radio/",
        "contact": "",
        "stream_url": "https://radio.radio-crestin.com/https/securestreams5.autopo.st:1951/;?type=http&nocache=15",
        "shoutcast_stats_url": "https://securestreams5.autopo.st:1951/stats?json=1"
    },
    {
        "id": 27,
        "title": "Radio Philadelphia Mansuè",
        "website": "http://www.philadelphiamansue.it/radio-philadelphia/",
        "contact": "",
        "stream_url": "https://radio.radio-crestin.com/http://94.130.106.91/radio/8000/radio.mp3",
    },
    {
        "id": 28,
        "title": "Radio Vocea Evangheliei Bucuresti",
        "website": "https://rvebucuresti.ro/",
        "contact": "contact@rvebucuresti.ro",
        "stream_url": "https://radio.radio-crestin.com/https/lb01.bpstream.com:8618/;",
        "shoutcast_stats_url": "https://lb01.bpstream.com:8618/stats?json=1"
    },
    {
        "id": 29,
        "title": "Radio Vocea Evangheliei Cluj",
        "website": "https://rvecj.ro/",
        "contact": "rvecluj@gmail.com",
        "stream_url": "https://radio.radio-crestin.com/https/s23.myradiostream.com/:18366/listen.mp3",
        "shoutcast_stats_url": "https://s23.myradiostream.com/:18366/stats?json=1"
    },
    {
        "id": 30,
        "title": "Radio Vocea Evangheliei Constanta",
        "website": "	http://rvect.ro",
        "contact": "contact@rvect.ro",
        "stream_url": "https://radio.radio-crestin.com/https://audio-rvectro.bisericilive.com/rvectro.mp3",
        "icecast_stats_url": "https://audio-rvectro.bisericilive.com/status-json.xsl?listen_url=rvectro",
    },
];
export const HISTORY_DATA_DIRECTORY_PATH="./public/history"
export const STATIONS_STATS_REFRESH_MS = 15000