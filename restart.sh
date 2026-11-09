#!/usr/bin/env bash
# Legacy Blueblue by NevermoreSSH (2022); modernized for reaganchomba/blueblue.
set -Eeuo pipefail
read -rp 'Service to restart (xray/nginx/stunnel5/ws-stunnel/dropbear/ssh): ' unit
case "$unit" in xray|nginx|stunnel5|ws-stunnel|dropbear|ssh) systemctl restart "$unit" ;; *) exit 1 ;; esac
