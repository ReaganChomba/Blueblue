#!/usr/bin/env bash
# Legacy Blueblue by NevermoreSSH (2022); modernized for reaganchomba/blueblue.
set -Eeuo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec bash "$ROOT/setup.sh" "$@"
