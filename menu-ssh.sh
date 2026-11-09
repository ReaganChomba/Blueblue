#!/usr/bin/env bash
# Legacy Blueblue by NevermoreSSH (2022); modernized for reaganchomba/blueblue.
set -Eeuo pipefail
while true; do
    echo 'SSH: 1) Add 2) Renew 3) Delete 4) List 5) Connections 0) Back'
    read -rp 'Choice: ' choice
    case "$choice" in
      1) blueblue-ssh add ;; 2) blueblue-ssh renew ;; 3) blueblue-ssh delete ;; 4) blueblue-ssh list ;; 5) blueblue-ssh sessions ;; 0) exit ;;
    esac
done
