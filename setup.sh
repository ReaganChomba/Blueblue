#!/usr/bin/env bash
# Legacy Blueblue by NevermoreSSH (2022); modernized for reaganchomba/blueblue.
set -Eeuo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if [[ ! -f "$ROOT/lib/install.sh" ]]; then
    [[ $EUID == 0 ]] || { echo 'Run as root' >&2; exit 1; }
    command -v python3 >/dev/null && command -v curl >/dev/null || {
        echo 'Install prerequisites: apt-get update && apt-get install -y ca-certificates curl python3' >&2; exit 1;
    }
    ref=${BLUEBLUE_REF:-modernization-2026}
    [[ $ref =~ ^[A-Za-z0-9._-]+$ ]] || { echo 'Invalid BLUEBLUE_REF'; exit 1; }
    bundle=$(mktemp -d)
    curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
        "https://api.github.com/repos/reaganchomba/blueblue/commits/$ref" -o "$bundle/commit.json"
    commit=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["sha"])' "$bundle/commit.json")
    [[ $commit =~ ^[0-9a-f]{40}$ ]] || exit 1
    echo "Retrieving project source at immutable commit $commit"
    curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
        "https://api.github.com/repos/reaganchomba/blueblue/tarball/$commit" -o "$bundle/source.tar.gz"
    python3 - "$bundle" <<'PY'
import pathlib,sys,tarfile
root=pathlib.Path(sys.argv[1])
with tarfile.open(root/'source.tar.gz') as tar:
    for m in tar.getmembers():
        if m.name.startswith('/') or '..' in pathlib.Path(m.name).parts or m.issym() or m.islnk() or not (m.isfile() or m.isdir()):
            raise SystemExit('Unsafe source archive')
    tar.extractall(root/'source')
PY
    roots=("$bundle"/source/*)
    (( ${#roots[@]} == 1 )) || exit 1
    ROOT=${roots[0]}
    echo "Source retained for inspection at $ROOT"
fi
source "$ROOT/lib/install.sh"
fresh_install "$@"
