#!/usr/bin/env bash
# Legacy Blueblue by NevermoreSSH (2022); modernized for reaganchomba/blueblue.
set -Eeuo pipefail
[[ $EUID == 0 ]] || exit 1
read -rp 'Daily reboot hour (0-23) or off: ' hour
if [[ $hour == off ]]; then rm -f /etc/cron.d/blueblue-reboot; exit; fi
[[ $hour =~ ^[0-9]+$ ]] && (( hour < 24 )) || exit 1
printf '0 %s * * * root /usr/sbin/reboot\n' "$hour" > /etc/cron.d/blueblue-reboot
chmod 644 /etc/cron.d/blueblue-reboot
