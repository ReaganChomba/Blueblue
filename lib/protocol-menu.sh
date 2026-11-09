#!/usr/bin/env bash
# Legacy Blueblue by NevermoreSSH (2022); modernized for reaganchomba/blueblue.
set -Eeuo pipefail
proto=${1:?Protocol required}
while true; do
    printf '\n%s accounts\n1) Add  2) Renew  3) Delete  4) List  5) Show links/export  6) Recent access  0) Back\n' "$proto"
    read -rp 'Choice: ' choice
    case "$choice" in
        1) if [[ $proto == vless ]]; then add-vless; else blueblue account "$proto" add; fi ;;
        2) blueblue account "$proto" renew ;;
        3) blueblue account "$proto" delete ;;
        4) blueblue account "$proto" list ;;
        5) blueblue account "$proto" show ;;
        6) blueblue activity "$proto" ;;
        0) exit ;;
        *) echo 'Unknown choice' ;;
    esac
done
