#!/usr/bin/env bash
# Legacy Blueblue by NevermoreSSH (2022); modernized for reaganchomba/blueblue.
set -Eeuo pipefail
for unit in ssh dropbear nginx xray stunnel5 ws-stunnel blueblue-expiry.timer; do
    systemctl --no-pager --full status "$unit" || true
done
