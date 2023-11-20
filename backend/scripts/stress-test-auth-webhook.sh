#!/bin/bash

# brew install plow

plow -n 10000 -c 100 -T application/json -H "Content-Type: application/json" http://127.0.0.1:8580/api/v1/webhook/authentication?session_id=2

#plow -n 10000 -c 100 --method "POST" -T application/json -H "Content-Type: application/json" --body '{"query":"query GetStations {\n  stations {\n    id\n    order\n    title\n    website\n    email\n    stream_url\n    proxy_stream_url\n    hls_stream_url\n    thumbnail_url\n    total_listeners\n    description\n    description_action_title\n    description_link\n    feature_latest_post\n    posts(limit: 1, order_by: { published: desc }) {\n      id\n      title\n      description\n      link\n      published\n    }\n    uptime {\n      is_up\n      latency_ms\n      timestamp\n    }\n    now_playing {\n      id\n      timestamp\n      song {\n        id\n        name\n        thumbnail_url\n        artist {\n          id\n          name\n          thumbnail_url\n        }\n      }\n    }\n    reviews {\n      id\n      stars\n      message\n    }\n  }\n  station_groups {\n    id\n    name\n    order\n    station_to_station_groups {\n      station_id\n      order\n    }\n  }\n}\n","variables":{},"operationName":"GetStations"}' https://graphql.radio-crestin.com/v1/graphql

