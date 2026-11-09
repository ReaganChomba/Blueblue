#!/usr/bin/env bash
# Legacy Blueblue by NevermoreSSH (2022); modernized for reaganchomba/blueblue.
set -Eeuo pipefail
echo 'Rotating managed logs using distribution logrotate policy.'
exec logrotate /etc/logrotate.conf
