#!/usr/bin/env bash
# Legacy Blueblue by NevermoreSSH (2022); modernized for reaganchomba/blueblue.
set -Eeuo pipefail
if command -v resolvectl >/dev/null; then exec resolvectl status; fi
cat /etc/resolv.conf
echo 'Change DNS through your network manager/netplan; Blueblue preserves resolver configuration.'
