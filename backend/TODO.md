### 3. Configure the Backup Module (`backend/superapp/apps/backups/settings.py`)

* Schedule it to run **once per week**.
* Retain **a maximum of 10 backups**.
* Only essential data should be backed up:

    * `stations_metadata_fetch`
    * `station_to_station_group`
    * `station_streams`
    * `reviews`
    * `posts`
    * `stations_uptime`
    * `stations_now_playing`
    * `stations`
    * `station_groups`
    * `station_metadata_fetch_categories`

---

### 4. Implement the HLS Stream Conversion Module

* This will be a **Python script** that:

    * Uses [`python-ffmpeg`](https://github.com/kkroening/ffmpeg-python) to generate and monitor `ffmpeg` processes (similar to `hls-streaming/generate_deployment.py`).
    * Connects to the backend via **GraphQL** to fetch a list of stations that require HLS conversion.
    * Refreshes the station list every **minute**, stopping or starting new `ffmpeg` processes accordingly.
    * Ensures the script **auto-restarts** if it stops.
    * Logs each `ffmpeg` process to `/tmp/logs/<radio_station_name>.log` with a **maximum size of 20MB**.
    * Implements a **metadata handler** that, when metadata changes, sends a GraphQL mutation to **trigger a metadata fetch** for the corresponding station.

---

### 5. Implement an NGINX Server for Compression

* NGINX configuration should be similar to `hls-streaming/nginx/nginx.conf`.

* It should run in a **container within the same pod** as the HLS converter.

* A separate **Python script** will:

    * make sure to register it and also the stremaing conversion module in backend/docker-compose.yml and create the script in `backend_hls_streaming` with it's own Dockerfile, keep it simple, small and use alpine, like in hls-streaming/Dockerfile 
    * Monitor the NGINX logs.
    * Send listener statistics for each station to the backend via a **GraphQL endpoint**.
    * Write data to:
      `backend/superapp/apps/radio_crestin/models/listening_events.py`
    * Send data in **batches every 10 seconds**.
    * Identify **unique users** using cookies:

        * Set a cookie in NGINX named `anonymous_session_id`
        * Example NGINX configuration:

      ```nginx
      http {
          map $cookie_anonymous_session_id $anonymous_session_id {
              default $request_id;
              ~.+ $cookie_anonymous_session_id;
          }
  
          log_format session_log '$remote_addr - $remote_user [$time_local] '
                                 '"$request" $status $body_bytes_sent '
                                 '"$http_referer" "$http_user_agent" '
                                 'anonymous_session_id="$anonymous_session_id"';
  
          server {
              listen 80;
              server_name example.com;
  
              access_log /var/log/nginx/session_access.log session_log;
  
              location / {
                  if ($cookie_anonymous_session_id = "") {
                      add_header Set-Cookie "anonymous_session_id=$request_id; Path=/; Max-Age=86400; HttpOnly";
                  }
  
                  ...
              }
          }
      }
      ```

* In `listening_events.py`, make sure to:

    * Track and update the `duration_seconds` field for every listening session based on the difference when the listening event started and current timestamp, if the difference between the last update is larger than a constant value (let's say 5 minutes, create a new session)
    * for each user, you will append only to the last session
    * refactor ListeningEvents model to ListeningSessions

* Update `radio_crestin.AppUsers` to store a reference to the `anonymous_session_id`.

---

### GraphQL Integration

* Modify the following code to also use the count of **unique active users** from `listening_events`:

    * An "active user" is defined as one who sent an event in the last **60 seconds**.

#### In `backend/superapp/apps/radio_crestin/graphql/types.py`

* Update:

  ```python
  @strawberry.field
  def radio_crestin_listeners(self) -> Optional[int]:
      """Get listener count specific to radio-crestin platform"""    
      return XXXXX
  ```

* And update:

  ```python
  @strawberry.field
  def total_listeners(self) -> Optional[int]:
      """Get current listener count from latest now playing data"""
      if hasattr(self, 'latest_station_now_playing') and self.latest_station_now_playing:
          return self.latest_station_now_playing.listeners
      return None
  ```

    * Ensure this also includes the count from `radio_crestin_listeners`.

- nu functioneaza HLS-ul asa de stabil, probabil pt ca container-ul nu este healthy si isi da restart?
