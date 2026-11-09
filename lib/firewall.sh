#!/usr/bin/env bash
# Explicit opt-in; preserves global policies and unrelated rules.
set -Eeuo pipefail
[[ $EUID == 0 ]] || { echo 'Root required' >&2; exit 1; }
proto=${1:?Usage: blueblue-firewall tcp|udp PORT}
port=${2:?Port required}
[[ $proto == tcp || $proto == udp ]] || exit 1
[[ $port =~ ^[0-9]+$ ]] && (( port > 0 && port < 65536 )) || exit 1
if command -v ufw >/dev/null && ufw status | grep -q '^Status: active'; then
    ufw allow "$port/$proto" comment Blueblue
elif command -v firewall-cmd >/dev/null && firewall-cmd --state >/dev/null 2>&1; then
    firewall-cmd --permanent --add-port="$port/$proto"
    firewall-cmd --add-port="$port/$proto"
elif command -v iptables >/dev/null; then
    iptables -C INPUT -p "$proto" --dport "$port" -m comment --comment Blueblue -j ACCEPT 2>/dev/null || \
        iptables -I INPUT -p "$proto" --dport "$port" -m comment --comment Blueblue -j ACCEPT
    echo 'iptables rule is runtime-only. Persist it using your existing firewall tooling.'
else
    echo 'Configure your nftables/host firewall manually.' >&2
    exit 1
fi
echo 'Also allow this port in the provider firewall. IPv6 rules, if needed, remain operator-managed.'
