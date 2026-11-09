#!/usr/bin/env bash
# Legacy Blueblue by NevermoreSSH (2022); modernized for reaganchomba/blueblue.
set -Eeuo pipefail
binary=$(python3 -c 'import json; print(json.load(open("/etc/blueblue/settings.json"))["binary"])')
exec "$binary" api statsquery --server=127.0.0.1:10085 "$@"
