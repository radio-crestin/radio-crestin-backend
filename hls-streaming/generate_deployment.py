import http.client
import json
import yaml

def get_stations():
    conn = http.client.HTTPSConnection("graphql.radio-crestin.com")

    payload = "{\"operationName\":\"GetStations\",\"query\":\"query GetStations {\\n  stations {\\n    id\\n    title\\n    stream_url \\n    slug\\n  }\\n}\\n\",\"variables\":{}}"

    headers = {
        'content-type': "application/json",
        'Authorization': "JWT "
    }

    conn.request("POST", "/v1/graphql", payload, headers)

    res = conn.getresponse()
    data = res.read()
    return json.loads(data.decode("utf-8"))["data"]["stations"]

def generate_deployment():
    deployment = {
        "version": "3.3",
        "services": {
            "hls_nginx": {
                "image": "nginx:1.21-alpine",
                "restart": "on-failure",
                "ports": [
                    "80:80"
                ],
                "volumes": [
                    "./nginx/nginx.conf:/etc/nginx/nginx.conf"
                ]
            },
        }
    }
    for station in get_stations():
        station_slug = station["slug"]
        station_stream = station["stream_url"]
        deployment["services"][f"hls_{station_slug}"] = {
            "build": {
                "context": "."
            },
            "volumes": [
                "/tmp/data:/data"
            ],
            "restart": "on-failure",
            "command": f"ffmpeg -y -i '{station_stream}' -c:a:0 libfdk_aac -profile:a:0 aac_he_v2 -b:a:0 32k -c:a:1 libfdk_aac -profile:a:1 aac_he_v2 -b:a:1 64k -c:a:2 libfdk_aac -profile:a:2 aac_he_v2 -b:a:2 128k -c:a:3 libmp3lame -b:a:3 320k -async 1 -ac 2 -r 44100 -map 0:a:0 -map 0:a:0 -map 0:a:0 -map 0:a:0 -f hls -hls_init_time 2 -hls_time 6 -hls_list_size 2 -hls_delete_threshold 10 -master_pl_name index.m3u8 -var_stream_map 'a:0,name:very_low,agroup:very_low a:1,name:low,agroup:low,default:yes a:2,name:medium,agroup:medium a:3,name:high,agroup:high' -hls_flags delete_segments+omit_endlist -hls_start_number_source epoch -master_pl_publish_rate 5 -method PUT -http_seekable 1 -http_persistent 1 -ignore_io_errors 1 -sc_threshold 0 /data/{station_slug}/%v/index.m3u8"
        }
    return deployment



if __name__ == '__main__':
    with open('docker-compose.yml', 'w') as yaml_file:
        yaml.dump(generate_deployment(), yaml_file, default_flow_style=False)