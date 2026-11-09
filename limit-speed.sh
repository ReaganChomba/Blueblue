#!/usr/bin/env bash
# Legacy Blueblue by NevermoreSSH (2022); modernized for reaganchomba/blueblue.
set -Eeuo pipefail
read -rp 'Interface: ' iface
ip link show dev "$iface" >/dev/null
read -rp 'Download Kbit/s: ' down
read -rp 'Upload Kbit/s: ' up
[[ $down =~ ^[0-9]+$ && $up =~ ^[0-9]+$ ]] || exit 1
# Distro wondershaper uses positional interface/down/up arguments.
exec wondershaper "$iface" "$down" "$up"
