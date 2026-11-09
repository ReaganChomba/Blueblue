#!/usr/bin/env bash
# Legacy Blueblue by NevermoreSSH (2022); modernized for reaganchomba/blueblue.
set -Eeuo pipefail
[[ $EUID == 0 ]] || { echo 'Root required'; exit 1; }
while true; do
    cat <<'MENU'
Blueblue 2026
1) SSH accounts        2) VMess accounts       3) VLESS accounts
4) Trojan accounts     5) Shadowsocks accounts 6) Expire accounts
11) Add Domains        12) Renew Certificate   14) Service status
15) Xray statistics    16) Speedtest           17) Bandwidth
18) Limit speed        21) Log rotation       22) Task manager
23) DNS information    55) Xray update guidance
66) Stock-kernel BBR    77) Memory             88) Backup
99) Restore accounts  101) Enable RAW TLS    102) Enable mKCP UDP
103) Enable HTTPUpgrade                       0) Exit
MENU
    read -rp 'Choice: ' choice
    case "$choice" in
      1) menu-ssh ;; 2) menu-vmess ;; 3) menu-vless ;; 4) menu-trojan ;; 5) menu-ss ;; 6) xp ;;
      11) blueblue-domain add ;; 12) blueblue-domain renew ;; 14) running ;;
      15) cek-trafik ;; 16) cek-speed ;; 17) cek-bandwidth ;; 18) limit-speed ;;
      21) clearlog ;; 22) htop ;; 23) dns ;; 55) xraychanger ;;
      66) bbr ;; 77) free -h ;; 88) backup ;; 99) restore ;;
      101) read -rp 'RAW TCP port [8443]: ' port; blueblue enable raw --port "${port:-8443}" ;;
      102) read -rp 'mKCP UDP port [40000]: ' port; blueblue enable kcp --port "${port:-40000}" ;;
      103) blueblue enable httpupgrade ;;
      0) exit ;;
      *) echo 'Unknown choice' ;;
    esac
done
