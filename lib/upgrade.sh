#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/install.sh"
platform
exec 9>/run/lock/blueblue.lock
flock -n 9 || die 'Another installer is running.'
exec 8>/run/lock/blueblue-domain.lock
flock -n 8 || die 'A certificate/domain operation is running.'
export BLUEBLUE_INSTALL_LOCKED=1
probe=$(python3 "$BLUEBLUE_ROOT/lib/probe.py")
export XRAY_BINARY XRAY_CONFIG XRAY_SERVICE
XRAY_BINARY=$(python3 -c 'import json,sys;print(json.load(sys.stdin)["binary"])' <<< "$probe")
XRAY_CONFIG=$(python3 -c 'import json,sys;print(json.load(sys.stdin)["config"])' <<< "$probe")
XRAY_SERVICE=$(python3 -c 'import json,sys;print(json.load(sys.stdin)["service"])' <<< "$probe")
xray_user=$(python3 -c 'import json,sys;print(json.load(sys.stdin)["user"])' <<< "$probe")
export XRAY_LOCATION_ASSET
XRAY_LOCATION_ASSET=$(python3 -c 'import json,sys;print(json.load(sys.stdin)["assets"])' <<< "$probe")
systemctl is-active --quiet "$XRAY_SERVICE" || die 'Xray must be running before upgrade.'
systemctl is-active --quiet nginx || die 'Nginx must be running before upgrade.'
backup="/var/backups/blueblue/$(date -u +%Y%m%dT%H%M%SZ)-$$"
python3 "$BLUEBLUE_ROOT/lib/snapshot.py" save "$backup" --extra "$XRAY_BINARY" --extra "$XRAY_CONFIG"
printf '%s\n' "$probe" > "$backup/probe.json"
printf '%s\n' "Backups: $backup"
# Capture original enablement and active states before replacing any service.
for unit in "$XRAY_SERVICE" nginx stunnel5 ws-stunnel blueblue-expiry.timer blueblue-cert-watch.path; do
    systemctl is-active "$unit" > "$backup/$unit.active" || true
    systemctl is-enabled "$unit" > "$backup/$unit.enabled" || true
done
rollback() {
    local status=${1:-1}
    trap - ERR INT TERM EXIT
    if [[ $blueblue_policy_owned == 1 ]]; then rm -f /usr/sbin/policy-rc.d; fi
    printf 'Upgrade failed; restoring files from %s\n' "$backup" >&2
    systemctl stop blueblue-expiry.timer blueblue-cert-watch.path stunnel5 ws-stunnel \
        blueblue-udpgw@7100 blueblue-udpgw@7200 blueblue-udpgw@7300 || true
    python3 "$BLUEBLUE_ROOT/lib/snapshot.py" restore "$backup" || true
    systemctl daemon-reload
    systemctl restart "$XRAY_SERVICE" || true
    systemctl reload nginx || true
    for unit in stunnel5 ws-stunnel blueblue-expiry.timer blueblue-cert-watch.path; do
        if grep -qx active "$backup/$unit.active"; then systemctl start "$unit" || true; fi
    done
    printf '%s\n' 'Package upgrades and certificate ACL additions are not undone. See docs/OPERATIONS.md.' >&2
    exit "$status"
}
trap 'rollback $?' ERR
trap 'rollback 130' INT
trap 'rollback 143' TERM
trap 'result=$?; if (( result != 0 )); then rollback "$result"; fi' EXIT
# Plan the config and Nginx patch before upgrading packages or replacing the binary.
# Stage only changes backed-up files; active processes retain their running config.
commands
python3 "$BLUEBLUE_ROOT/lib/blueblue.py" migrate --stage
stage=$(mktemp -d)
stage_xray "$stage"
packages
# Freshly staged core must accept the merged config before replacing the installed binary.
"$stage/xray" run -test -config "$XRAY_CONFIG"
nginx -t
# Grant the existing service user access to its existing custom certificate for optional RAW TLS.
cert=$(python3 -c 'import json;print(json.load(open("/etc/blueblue/settings.json"))["certificate"])')
key=$(python3 -c 'import json;print(json.load(open("/etc/blueblue/settings.json"))["private_key"])')
[[ -r "$cert" && -r "$key" ]] || die 'Existing certificate/key not readable.'
install_xray_assets "$stage" "$XRAY_BINARY"
# Migrate only the Blueblue-owned Stunnel instance, retaining section ports and certificate paths.
systemctl stop stunnel5 ws-stunnel
python3 "$BLUEBLUE_ROOT/lib/stunnel.py" --stage
systemctl daemon-reload
python3 - "$BLUEBLUE_ROOT/lib" "$XRAY_CONFIG" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
from blueblue import SETTINGS, read_json, validate_xray
validate_xray(read_json(SETTINGS, {}), sys.argv[2])
PY
systemctl enable stunnel5 ws-stunnel
systemctl restart "$XRAY_SERVICE"
systemctl reload nginx
systemctl start stunnel5 ws-stunnel
python3 "$BLUEBLUE_ROOT/lib/blueblue.py" refresh
expiry_timer
certificate_watch
if [[ -x /usr/bin/badvpn-udpgw || ${BLUEBLUE_ENABLE_UDPGW:-0} == 1 ]]; then
    bash "$BLUEBLUE_ROOT/install-udpgw.sh"
fi
trap - ERR INT TERM EXIT
printf 'Upgrade complete. Backup: %s\nRelease files: %s\n' "$backup" "$stage"
printf '%s\n' 'No certificate issuance or renewal was requested. See docs/OPERATIONS.md for rollback.'
