#!/usr/bin/env bash
# Legacy Blueblue by NevermoreSSH (2022); modernized for reaganchomba/blueblue.
set -Eeuo pipefail
apt-get update
apt-get install -y vnstat
systemctl enable --now vnstat
