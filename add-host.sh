#!/usr/bin/env bash
# Legacy Blueblue by NevermoreSSH (2022); modernized for reaganchomba/blueblue.
set -Eeuo pipefail
# DNS records are operator-owned; no shared Cloudflare credentials.
exec blueblue-domain add "$@"
