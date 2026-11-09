#!/usr/bin/env bash
# Legacy Blueblue by NevermoreSSH (2022); modernized for reaganchomba/blueblue.
set -Eeuo pipefail
[[ $EUID == 0 ]] || exit 1
modprobe tcp_bbr
cat > /etc/sysctl.d/90-blueblue-bbr.conf <<'EOF'
net.core.default_qdisc=fq
net.ipv4.tcp_congestion_control=bbr
EOF
sysctl -p /etc/sysctl.d/90-blueblue-bbr.conf
