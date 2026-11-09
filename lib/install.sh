#!/usr/bin/env bash
# Shared installer, sourced only by checked-in entrypoints.
set -Eeuo pipefail
umask 027
BLUEBLUE_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
export DEBIAN_FRONTEND=noninteractive
blueblue_policy_owned=0

die() { printf '%s\n' "Blueblue: $*" >&2; exit 1; }
platform() {
    [[ $EUID == 0 ]] || die 'Run as root.'
    [[ -d /run/systemd/system ]] || die 'systemd is required.'
    . /etc/os-release
    case "$ID:$VERSION_ID" in
        ubuntu:22.04|ubuntu:24.04|debian:12|debian:13) ;;
        *) die "Unsupported distribution: $ID $VERSION_ID. Upgrade the OS separately." ;;
    esac
    printf 'Platform: %s %s, %s\n' "$ID" "$VERSION_ID" "$(uname -m)"
}
packages() {
    apt-get update
    # Only managed dependencies; no full-system upgrade, purges or firewall policy changes.
    # Prevent package postinst from restarting existing services during staging.
    [[ ! -e /usr/sbin/policy-rc.d ]] || die 'Existing policy-rc.d found; arrange package maintenance separately.'
    printf '#!/bin/sh\nexit 101\n' > /usr/sbin/policy-rc.d
    blueblue_policy_owned=1
    chmod 755 /usr/sbin/policy-rc.d
    local status=0
    NEEDRESTART_MODE=l apt-get -o Dpkg::Options::=--force-confold install -y --no-install-recommends \
        ca-certificates curl wget git jq unzip python3 nginx stunnel4 openssh-server dropbear \
        openssl socat cron acl vnstat speedtest-cli rclone logrotate iproute2 procps \
        lsof net-tools bc htop iftop dnsutils wondershaper certbot || status=$?
    rm -f /usr/sbin/policy-rc.d
    blueblue_policy_owned=0
    return "$status"
}
commands() {
    install -d -m 755 /usr/local/lib/blueblue /usr/bin
    cp -a "$BLUEBLUE_ROOT/lib/." /usr/local/lib/blueblue/
    install -d -m 700 /etc/blueblue
    local file name
    for file in add-vless add-ws add-tr add-ssws add-socks add-trgo menu-vless menu-vmess \
        menu-trojan menu-ss menu-socks menu-trgo menu-ssh usernew user-xrays del-xrays xp \
        backup restore menu menu4 cf cfa add-host restart running cek-bandwidth cek-trafik \
        clearlog logcleaner bbr dns limit-speed tendang autoreboot webmin cekv; do
        install -m 755 "$BLUEBLUE_ROOT/$file.sh" "/usr/bin/$file"
    done
    install -m 755 "$BLUEBLUE_ROOT/menu-bckp-github.sh" /usr/bin/menu-bckp
    install -m 755 "$BLUEBLUE_ROOT/menu-bckp-telegram.sh" /usr/bin/menu-bckp-telegram
    install -m 755 "$BLUEBLUE_ROOT/add-host.sh" /usr/bin/addhost
    install -m 755 "$BLUEBLUE_ROOT/speedtest_cli.py" /usr/bin/cek-speed
    install -m 755 "$BLUEBLUE_ROOT/ram.sh" /usr/bin/cek-ram
    cat > /usr/bin/blueblue <<'EOF'
#!/usr/bin/env bash
set -Eeuo pipefail
exec python3 /usr/local/lib/blueblue/blueblue.py "$@"
EOF
    chmod 755 /usr/bin/blueblue
    install -m 755 "$BLUEBLUE_ROOT/lib/ssh-account.py" /usr/bin/blueblue-ssh
    install -m 755 "$BLUEBLUE_ROOT/lib/domain.sh" /usr/bin/blueblue-domain
    install -m 755 "$BLUEBLUE_ROOT/lib/backup.py" /usr/bin/blueblue-backup
    install -m 755 "$BLUEBLUE_ROOT/lib/firewall.sh" /usr/bin/blueblue-firewall
    # Legacy aliases invoke the same manager, never download replacement scripts.
    ln -sf /usr/bin/menu /usr/bin/menu-update
    cat > /usr/bin/xraychanger <<'EOF'
#!/usr/bin/env bash
echo 'Use the reviewed upgrade-existing.sh bundle to upgrade Xray with a backup.'
EOF
    chmod 755 /usr/bin/xraychanger
}
expiry_timer() {
    cat > /etc/systemd/system/blueblue-expiry.service <<'EOF'
[Unit]
Description=Expire Blueblue proxy and SSH accounts
After=network.target
[Service]
Type=oneshot
ExecStart=/usr/bin/xp
UMask=0077
EOF
    cat > /etc/systemd/system/blueblue-expiry.timer <<'EOF'
[Unit]
Description=Check Blueblue account expiry each minute
[Timer]
OnCalendar=*-*-* *:*:00
Persistent=true
[Install]
WantedBy=timers.target
EOF
    systemctl daemon-reload
    systemctl enable --now blueblue-expiry.timer
}
certificate_watch() {
    python3 - <<'PY'
import json
from pathlib import Path
s=json.loads(Path('/etc/blueblue/settings.json').read_text())
for key in ('certificate','private_key'):
    if any(c.isspace() for c in s[key]):
        raise SystemExit('Certificate paths with whitespace need a manually configured watcher')
Path('/etc/systemd/system/blueblue-cert-watch.path').write_text('''[Unit]
Description=Watch existing Blueblue certificate files
[Path]
PathChanged={certificate}
PathChanged={private_key}
Unit=blueblue-cert-watch.service
[Install]
WantedBy=multi-user.target
'''.format(**s))
Path('/etc/systemd/system/blueblue-cert-watch.service').write_text('''[Unit]
Description=Reload Blueblue certificate consumers after existing ACME renewal
[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /usr/local/lib/blueblue/cert-watch.py
UMask=0077
''')
PY
    systemctl daemon-reload
    systemctl enable --now blueblue-cert-watch.path
}
stage_xray() {
    local stage=$1
    python3 "$BLUEBLUE_ROOT/lib/blueblue.py" release "$stage"
}
install_xray_assets() {
    local stage=$1 binary=$2
    install -d -m 755 /usr/local/share/xray
    # Keep customized geodata already present. Release geodata initializes missing files only.
    local name
    for name in geoip.dat geosite.dat; do
        if [[ -f "$stage/$name" && ! -f "/usr/local/share/xray/$name" ]]; then
            install -m 644 "$stage/$name" "/usr/local/share/xray/$name"
        fi
    done
    install -m 755 "$stage/xray" "${binary}.blueblue-new"
    mv -f -- "${binary}.blueblue-new" "$binary"
    install -m 600 "$stage/release.json" /etc/blueblue/xray-release.json
}
fresh_install() {
    platform
    exec 9>/run/lock/blueblue.lock
    flock -n 9 || die 'Another Blueblue operation is running.'
    export BLUEBLUE_INSTALL_LOCKED=1
    [[ ! -e /etc/xray/config.json && ! -e /usr/local/etc/xray/config.json ]] || die 'Existing Xray found; use upgrade-existing.sh.'
    # Refuse existing listeners, rather than replace another site's configuration.
    if ss -H -ltn | awk '{print $4}' | grep -Eq ':(80|443|700|109|143|447|777)$'; then
        die 'A required fresh-install port is occupied. Use a separate server or the live upgrade.'
    fi
    packages
    commands
    install -d -m 750 -o root -g www-data /etc/xray
    install -d -m 755 /home/vps/public_html/.well-known/acme-challenge
    local stage
    stage=$(mktemp -d)
    stage_xray "$stage"
    install_xray_assets "$stage" /usr/local/bin/xray
    export XRAY_CONFIG=/etc/xray/config.json
    python3 "$BLUEBLUE_ROOT/lib/blueblue.py" fresh
    chown root:www-data /etc/xray/config.json
    chmod 640 /etc/xray/config.json
    install -m 644 "$BLUEBLUE_ROOT/systemd/xray.service" /etc/systemd/system/xray.service
    # Distribution defaults remain intact. This only adds Dropbear's Blueblue ports.
    if ! grep -q 'BLUEBLUE' /etc/default/dropbear; then
        cp -a /etc/default/dropbear /etc/blueblue/dropbear.defaults.original
        cat >> /etc/default/dropbear <<'EOF'
# BLUEBLUE
NO_START=0
DROPBEAR_PORT=143
DROPBEAR_EXTRA_ARGS="-p 109"
EOF
    fi
    grep -qxF /bin/false /etc/shells || printf '/bin/false\n' >> /etc/shells
    python3 "$BLUEBLUE_ROOT/lib/stunnel.py" --fresh
    cat > /root/log-install.txt <<'EOF'
Blueblue XRAY (2026)
OpenSSH : 22
Dropbear : 109, 143
SSH Websocket : 80
SSH SSL Websocket : 443
Stunnel5 : 447, 777
Vless TLS : 443
Vless None TLS : 80
Vmess TLS : 443
Vmess None TLS : 80
Trojan WS : 443
Sodosok WS/GRPC : 443
UDPGW : optional; see README
EOF
    systemctl daemon-reload
    /usr/local/bin/xray run -test -config /etc/xray/config.json
    nginx -t
    systemctl enable --now xray dropbear ssh ws-stunnel
    systemctl enable nginx
    systemctl reload-or-restart nginx
    expiry_timer
    certificate_watch
    if [[ ${BLUEBLUE_ENABLE_UDPGW:-0} == 1 ]]; then bash "$BLUEBLUE_ROOT/install-udpgw.sh"; fi
    printf '%s\n' 'Installed. Open menu -> Add Domains -> Renew Certificate to activate HTTPS and Stunnel.'
    printf 'Verified release staging files retained at %s\n' "$stage"
}
