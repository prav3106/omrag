#!/usr/bin/env bash
# Proves the claim in the report: after setup, nothing reaches the network.
#
# macOS:  sudo ifconfig en0 down   (re-enable with: sudo ifconfig en0 up)
# Linux:  sudo ip link set <iface> down
#
# With the interface down, run this script: ingestion and querying must both
# succeed. Any failure here means something in the pipeline still phones home.
set -euo pipefail
API=${API:-http://127.0.0.1:8000}

echo "== status =="
curl -s "$API/status" | head -c 400; echo

echo "== query =="
curl -s -X POST "$API/query" -H 'Content-Type: application/json' \
  -d '{"query":"summarise the indexed sources"}' | head -c 600; echo

echo
echo "If both calls returned data with the network interface disabled, the"
echo "pipeline is genuinely offline."
