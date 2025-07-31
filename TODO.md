### Backend TODO
~~- [ ] converteste proiectul la superapp~~
~~- [ ] renunta la hasura si pune toata logica in superapp~~
~~- [ ] creaza engine-ul care colecteaza date despre numarul de ascultatori HLS~~
~~- [ ] adauga autentificare pentru mutations~~
~~- [ ] adauga ingress si configureaza cloudflare tunnel~~
~~- [ ] configureaza caching la nivel de nginx in ingress~~
~~- [ ] asigura-te ca metadatele sunt actualizate corect~~
- [ ] asigura-te ca hls streaming face push corect la numarul de ascultatori
- [ ] si deasemenea ip-ul utilizatorilor e corect
- [ ] apoi afiseaza metadatele corect
- [ ] apoi rezolva homepage-ul si asigura-te ca intreg website-ul e functional
- [ ] creaza o versiune putin diferita pentru radio-crestin.com 
- [ ] creaza un env de staging unde sa testam noul env
- [ ] implementeaza metadata scraping pentru Radio King (https://radio.voceacrestinilor.com/ - https://api.radioking.io/widget/radio/radio-vocea-crestinilor/track/current)
- [ ] adauga scraping pentru https://www.philadelphiachurch.com.au/radio-philadelphia


Frontend:
- [ ] header-ul trebuie sa fie rendered server-side
- [X] make the play button & volume icon a bit smaller && make the volume slider width constant
- [ ] implement random station functionality
- [X] when selecting a station, the player should start automatically
- [ ] implement add to favorite functionality
- [ ] implement stations groups
- [ ] sort all stations to left
- [ ] make the stations thumbnail a bit smaller
- [ ] add current played song as head meta (maybe Google will pick them and display in search results)
- [ ] create a page for each station (and simulate a page redirect when clicking on a station)
- [ ] create a sitemap with all the stations
- [ ] create a subdomain for each station (just the player + the latest articles)
- [ ] allow the user to add a shortcut on desktop for the app
- [ ] create am embeddable player
- [ ] add SEO meta for all the reviews
- [ ] make the website mobile responsive
- [ ] refresh the station metadata every 5 seconds
- [ ] implement add to favorite each station
- [ ] optimize the website for maximum performance on web.dev
- [ ] implement HLS player on website
- [ ] populate station description from API
- [ ] allow the user to leave a review (/api/v1/review)
- [ ] create a pop-up so that the user can share Radio Crestin with their friends
- [ ] enable server side rendering and push the website to a very fast CDN
- [ ] link each station to the correct Facebook page by using the link from API
- [ ] improve the website audio player to allow the user to select which stream should be played for that station (hls/proxy/original)
- [ ] when a stream is failing, fall-back to the next stream automatically
- [ ] when a station is playing, send this signal to backend (send station_id every 15 seconds)
- [ ] add facebook page as SEO meta field
- [ ] SEO meta field - current playing
- [ ] send the listened station every 1 minute (/api/v1/listen)
- [ ] sum up to station listeners the radio_crestin_listeners value when the user is listening using the HLS or proxy
- [ ] allow the user to report a problem (also, send current timestamp, his IP and all the console logs)
Backend:
- start station when clicking on the thumbnail
- make sure that we're not abusing the shoutcast endpoints
- limit the maximum number of requests to graphql to 5 per second
- whitelist all of our servers IPs on Aripi Spre Cer
- implement a system to suggest what to listen next based on the amount of time the station was listened by users
- zero downtime docker deployment using docker swarm
- "aggregate" listeners events & clean up them
- enable gzip compression also for api responses
- add audio normalization (http://ffmpeg.org/ffmpeg-all.html#loudnorm) or maybe something on the client side
- add more stations
- upload hls to edge CDNs (for now we will let Bunny to pull the data, later on we might want to sync the files directly to Bunny..)
- add aripi spre cer monitoring based on shoutcast metadata
