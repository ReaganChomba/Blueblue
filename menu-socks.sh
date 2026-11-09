#!/usr/bin/env bash
# Legacy Blueblue by NevermoreSSH (2022); modernized for reaganchomba/blueblue.
set -Eeuo pipefail
exec bash /usr/local/lib/blueblue/protocol-menu.sh socks "$@"
