#!/usr/bin/env bash
# Legacy Blueblue by NevermoreSSH (2022); modernized for reaganchomba/blueblue.
set -Eeuo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$ROOT/lib/install.sh"
platform
apt-get update
apt-get install -y rclone wondershaper
commands
echo 'Configure your own rclone destination with rclone config. No account configuration was downloaded.'
