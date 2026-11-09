#!/usr/bin/env bash
# Optional legacy SSH UDPGW compatibility, built from a resolved upstream release commit.
set -Eeuo pipefail
umask 027
[[ $EUID == 0 ]] || exit 1
source_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
apt-get update
apt-get install -y --no-install-recommends build-essential cmake git ca-certificates curl python3
stage=$(mktemp -d)
curl --fail --silent --show-error --location --proto '=https' \
    https://api.github.com/repos/ssrlive/badvpn/releases/latest -o "$stage/release.json"
tag=$(python3 - "$stage/release.json" <<'PY'
import json,sys,re
r=json.load(open(sys.argv[1]))
if r['prerelease'] or r['draft'] or not re.fullmatch(r'[A-Za-z0-9._-]+',r['tag_name']):
    raise SystemExit('A stable release is required')
print(r['tag_name'])
PY
)
curl --fail --silent --show-error --location --proto '=https' \
    "https://api.github.com/repos/ssrlive/badvpn/commits/$tag" -o "$stage/commit.json"
commit=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["sha"])' "$stage/commit.json")
[[ $commit =~ ^[0-9a-f]{40}$ ]] || exit 1
git init "$stage/source"
git -C "$stage/source" remote add release https://github.com/ssrlive/badvpn.git
git -C "$stage/source" fetch --depth 1 release "$commit"
[[ $(git -C "$stage/source" rev-parse FETCH_HEAD) == "$commit" ]] || exit 1
git -C "$stage/source" checkout --detach FETCH_HEAD
cmake -S "$stage/source" -B "$stage/build" -DBUILD_NOTHING_BY_DEFAULT=1 -DBUILD_UDPGW=1 -DCMAKE_BUILD_TYPE=Release
cmake --build "$stage/build" --parallel 2
install -m 755 "$stage/build/udpgw/badvpn-udpgw" /usr/local/bin/badvpn-udpgw
# Capture source identity for reproducibility; never install the old bundled ELF.
install -d -m 700 /etc/blueblue
cp "$stage/release.json" /etc/blueblue/udpgw-release.json
printf '%s\n' "$commit" > /etc/blueblue/udpgw-source-commit
if [[ -f /etc/rc.local ]]; then
    python3 - <<'PY'
from pathlib import Path
p=Path('/etc/rc.local')
lines=p.read_text().splitlines(keepends=True)
p.write_text(''.join(line for line in lines if not
    (line.strip().startswith('screen -dmS badvpn badvpn-udpgw --listen-addr 127.0.0.1:') and
     any(':'+str(port)+' ' in line for port in (7100,7200,7300)))))
PY
fi
# Retire only screen sessions named exactly badvpn; never stop rc-local or other sessions.
if command -v screen >/dev/null; then
    while read -r session; do
        [[ $session =~ ^[0-9]+\.badvpn$ ]] || continue
        screen -S "$session" -X quit
    done < <(screen -ls | awk '$1 ~ /^[0-9]+\.badvpn$/ {print $1}')
fi
for port in 7100 7200 7300; do
    if ss -H -ltn | awk '{print $4}' | grep -q ":$port$"; then
        # A prior managed instance is safe to restart; an unrelated listener is not.
        systemctl is-active --quiet "blueblue-udpgw@$port" || { echo "Port $port occupied" >&2; exit 1; }
    fi
done
cat > /etc/systemd/system/blueblue-udpgw@.service <<'EOF'
[Unit]
Description=Blueblue SSH UDPGW compatibility on loopback %i
After=network.target
[Service]
DynamicUser=yes
ExecStart=/usr/local/bin/badvpn-udpgw --listen-addr 127.0.0.1:%i --max-clients 500
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
LimitNOFILE=8192
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now blueblue-udpgw@7100 blueblue-udpgw@7200 blueblue-udpgw@7300
systemctl restart blueblue-udpgw@7100 blueblue-udpgw@7200 blueblue-udpgw@7300
if [[ -f /usr/bin/badvpn-udpgw && ! -L /usr/bin/badvpn-udpgw ]]; then
    cp -a /usr/bin/badvpn-udpgw "/etc/blueblue/legacy-udpgw.$(date -u +%Y%m%dT%H%M%SZ)"
fi
ln -sf /usr/local/bin/badvpn-udpgw /usr/bin/badvpn-udpgw
echo "UDPGW source $tag ($commit); build files retained at $stage. No public UDPGW port opened."
