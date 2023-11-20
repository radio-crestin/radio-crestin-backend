#!/bin/bash

# brew install plow

plow -n 10000 -c 100 -T application/json -H "Content-Type: application/json" http://127.0.0.1:8086/api/v1/webhook/authentication?session_id=1

