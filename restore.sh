#!/usr/bin/env bash
# Legacy Blueblue by NevermoreSSH (2022); modernized for reaganchomba/blueblue.
set -Eeuo pipefail
if (( $# == 0 )); then
    read -rp 'Local Blueblue .tar.gz backup path: ' archive
    set -- "$archive"
fi
exec blueblue-backup restore "$@"
