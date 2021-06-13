var empty_song = {
    "id": "&nbsp;",
    "title": "&nbsp;",
    "artist": "&nbsp;",
    "duration": "&nbsp;",
    "lyrics": "&nbsp;",
    "album": "&nbsp;",
    "isRequested": "&nbsp;",
    "isDedication": "",
    "dedicationName": "&nbsp;",
    "dedicationMessage": "&nbsp;",
    "datePlayed": "",
    "listeners": "&nbsp;",
    "genre": "&nbsp;",
    "listeners_count": "&nbsp;",
    "song_favorite": "&nbsp;",
    "picture": ""
};
var isPlaying = false;
var player;
var stationID = 0;
var latest_song_title = "";
var website_title = [];
var website_title_index = 0;
var hidden, visibilityChange;

const MELODII_RECENTE_BY_STATION_ID = {
    0: "https://www.aripisprecer.ro/request/web/playing.php?buster=05094957150",
    4: "https://www.aripisprecer.ro/request_predici/web/playing.php?buster=05094957150",
    3: "https://www.aripisprecer.ro/request_worship/web/playing.php?buster=05094957150",
    5: "https://www.aripisprecer.ro/request_w2h/web/playing.php?buster=05094957150",
    6: "https://www.aripisprecer.ro/request_instrumental/web/playing.php?buster=05094957150",
    7: "https://www.aripisprecer.ro/request_popular/web/playing.php?buster=05094957150",
}

function generate_song_html(song) {
    'use strict';
    var template = document.querySelector("#song_template").cloneNode(true);
    template.id = "";
    template.style.display = "block";
    if (song['picture'].length > 0) {
        template.querySelector(".song_picture > .picture").style.backgroundImage = 'url("' + song['picture'] + ');';
    }
    template.querySelector(".song_name").innerHTML = song['title'];
    template.querySelector(".album_name").innerHTML = song['album'];
    template.querySelector(".author_name").innerHTML = song['artist'];
    if (song['isDedication']) {
        template.querySelector(".dedication").style.display = "block";
        template.querySelector(".song_information").style.marginTop = "0 px";
        template.querySelector(".dedication_name").innerHTML = song['dedicationName'];
        template.querySelector(".dedication_message").innerHTML = song['dedicationMessage'];
    }
    template.querySelector(".song_datePlayed").innerHTML = song['datePlayed'];
    template.querySelector(".recently_played_songs_link").href = MELODII_RECENTE_BY_STATION_ID[stationID];
    template.querySelector("#listeners_count_number").innerHTML = song['listeners_count'] + ' ascultatori';

    if ('mediaSession' in navigator) {
        navigator.mediaSession.metadata = new MediaMetadata({
            title: song['title'],
            artist: song['artist'],
            album: song['album'],
            artwork: [{
                src: song['picture'],
                type: 'image/jpg'
            }, ]
        });
    }

    if(isPlaying) {
        website_title = [song['title'], song['artist']];
    } else {
        website_title = [];
    }
    updatePageTitle(true);

    return template;
}

function loadNowPlayingPlaceholder() {
    'use strict';
    var song_html = generate_song_html(empty_song);
    song_html.classList.add("now_playing");
    song_html.classList.add("template_is_loading");
    document.querySelector("#now_playing_container").innerHTML = '';
    document.querySelector("#now_playing_container").appendChild(song_html);
}

function updateNowPlaying() {
    'use strict';
    var url = "/request/android/now_playing_new.php?station_id=" + stationID + "&r=" + Math.floor(Math.random() * 9999999999);
    var success_handler = function(data) {

        var song_html = generate_song_html(data[0]);
        song_html.classList.add("now_playing");
        document.querySelector("#now_playing_container").innerHTML = '';
        document.querySelector("#now_playing_container").appendChild(song_html);


        if (latest_song_title === data[0]['title']) {
            return;
        }
        latest_song_title = data[0]['title'];

        setTimeout(function() {
            updateNowPlaying();
        }, parseInt(data[0]['duration']) / 2);

        setTimeout(function() {
            updateNowPlaying();
        }, parseInt(data[0]['duration']) + 24000);
    };
    fetch(url).then(function(response) {
        return response.json();
    }).then(success_handler)
        .catch(function(error) {
            console.log("error accessing the latest song", error);
        });

}

var lastPlayerSource = {};

function selectStation(name, link, station_id) {
    player.elements.display.currentStation.textContent = "Se incarca..";
    stationID = station_id;
    updateNowPlaying();
    player.source = {
        type: 'audio',
        title: name,
        sources: [{
            src: link,
            type: 'audio/mp3'
        }]
    };
    lastPlayerSource = {
        type: 'audio',
        title: name,
        sources: [{
            src: link,
            type: 'audio/mp3'
        }]
    };
};

var remaining_retries = 5;
var remaining_error_retries = 5;

function updatePageTitle(resetIndex = false) {
    if(website_title_index > website_title.length - 1) {
        website_title_index = 0;
    }
    if(resetIndex) {
        website_title_index = 0;
    }

    if (!document[hidden]) {
        if (typeof website_title[website_title_index] !== "undefined" && isPlaying) {
            document.title = `${website_title[website_title_index]} | Aripi Spre Cer`;
        } else {
            document.title = `Radio Crestin Aripi Spre Cer`;
        }
    } else {
        document.title = `Radio Crestin Aripi Spre Cer`;
    }
}

(function() {
    loadNowPlayingPlaceholder();
    updateNowPlaying();

    setInterval(function() {
        updatePageTitle();
    }, 7500);


    let touch_device = (navigator.maxTouchPoints || 'ontouchstart' in document.documentElement);
    let controls = ['play', 'current-station', 'current-time', 'mute', 'volume', 'pip', 'airplay', 'settings'];
    if (touch_device) {
        controls = ['play', 'current-station', 'current-time', 'pip', 'airplay', 'settings'];
    }
// init Plyr player
    player = new Plyr('#playerAripi', {
        debug: false,
        controls: controls,
        settings: ['quality'],
        autoplay: false,
        volume: 0.8,
        resetOnEnd: true,
        language: 'ro',
        invertTime: false,
    }); player.on('loadstart', function(event) {
        player.elements.display.currentStation.textContent = 'Se incarca..';
    }); player.on('playing', function(event) {
        player.elements.display.currentStation.textContent = player.config.title;
        isPlaying = true;
        updateNowPlaying();
        remaining_retries = 5;
    });player.on('pause', function(event) {
        isPlaying = false;
        updatePageTitle(true);
    });player.on('emptied', function(event) {
        isPlaying = false;
        updatePageTitle(true);
    }); player.on('loadeddata', function(event) {
        player.elements.display.currentStation.textContent = player.config.title;
    }); player.on('waiting', function(event) {
        player.elements.display.currentStation.textContent = 'Se incarca..';
    }); player.on('stalled', function(event) {
        // player.elements.display.currentStation.textContent = 'A aparut o problema neasteptata.';
        // player.pause();
        console.trace('stalled', event)
        if (!player.media.paused && remaining_retries > 0) {
            setTimeout(function() {
                console.log("Retrying to play..")
                player.source = lastPlayerSource;
                player.play();
                remaining_retries--;
            }, remaining_retries === 5 ? 0 : 1000);
        }
    }); player.on('error', function(event) {
        console.trace('error', event)
        if (!player.media.paused && event.detail.plyr.media.error && event.detail.plyr.failed && remaining_error_retries > 0) {
            setTimeout(function() {
                console.log("Retrying to play..")
                player.source = lastPlayerSource;
                player.play();
                remaining_error_retries--;
            }, remaining_error_retries === 5 ? 0 : 1000);
        }

    });


// update station selection
    var selectedStationElem = document.querySelector(".playerStations > a.active"); selectStation(selectedStationElem.text, selectedStationElem.href, selectedStationElem.dataset.stationId);

    document.querySelectorAll(".playerStations > a").forEach(function(item) {
        item.onclick = function(event) {
            event.preventDefault();
            var activeElem = document.querySelector(".playerStations > a.active");
            if (activeElem) {
                activeElem.className = "";
            }
            this.className = "active";
            selectStation(this.text, this.href, this.dataset.stationId);
            player.restart();
            player.play();
        };
    });

    if (typeof document.hidden !== "undefined") { // Opera 12.10 and Firefox 18 and later support
        hidden = "hidden";
        visibilityChange = "visibilitychange";
    } else if (typeof document.msHidden !== "undefined") {
        hidden = "msHidden";
        visibilityChange = "msvisibilitychange";
    } else if (typeof document.webkitHidden !== "undefined") {
        hidden = "webkitHidden";
        visibilityChange = "webkitvisibilitychange";
    }

    function handleVisibilityChange() {
        if (document[hidden]) {
            website_title = [];
            updatePageTitle(true);
        } else {
            updateNowPlaying();
        }
    }
    document.addEventListener(visibilityChange, handleVisibilityChange, false);

})();
