#!/usr/bin/env bash
# Legacy Blueblue by NevermoreSSH (2022); modernized for reaganchomba/blueblue.
set -Eeuo pipefail
if (( $# )); then exec blueblue account vless add "$@"; fi
read -rp 'Transports (comma-separated enabled names; Enter for all enabled): ' transports
if [[ -n $transports ]]; then
    exec blueblue account vless add --transports "$transports"
fi
exec blueblue account vless add
