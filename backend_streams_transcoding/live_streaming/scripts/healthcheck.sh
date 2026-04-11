#!/bin/sh
# Health check — delegates to the health server which validates
# DASH manifest freshness, HLS segment freshness, and segment existence.
# Used by both Docker HEALTHCHECK and Kubernetes probes (via NGINX proxy).
wget -q -O /dev/null http://localhost:8080/health || exit 1
exit 0
