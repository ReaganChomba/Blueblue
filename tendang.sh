#!/usr/bin/env bash
# Legacy Blueblue by NevermoreSSH (2022); modernized for reaganchomba/blueblue.
set -Eeuo pipefail
echo 'SSH account session limits should be set explicitly in /etc/security/limits.d/.'
echo 'Automatic session killing and SSH daemon restarts are disabled. Current sessions:'
exec who
