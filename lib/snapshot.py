#!/usr/bin/env python3
"""Root-only timestamped rollback archive and explicit absence manifest."""
import argparse
import base64
import json
import os
from pathlib import Path
import shutil
import tarfile

COMMANDS = '''add-vless add-ws add-tr add-ssws add-socks add-trgo menu-vless menu-vmess menu-trojan
menu-ss menu-socks menu-trgo menu-ssh usernew user-xrays del-xrays xp backup restore menu menu4
cf cfa add-host restart running cek-bandwidth cek-trafik clearlog logcleaner bbr dns limit-speed
tendang autoreboot webmin cekv menu-bckp menu-bckp-telegram addhost cek-speed cek-ram blueblue
blueblue-ssh blueblue-domain blueblue-backup blueblue-firewall menu-update xraychanger'''.split()
PATHS = ['/etc/xray', '/usr/local/etc/xray', '/etc/nginx', '/etc/blueblue', '/etc/stunnel5',
         '/home/vps/public_html',
         '/usr/bin/badvpn-udpgw', '/usr/local/bin/badvpn-udpgw', '/etc/rc.local',
         '/etc/systemd/system/blueblue-udpgw@.service',
         '/etc/systemd/system/multi-user.target.wants/blueblue-udpgw@7100.service',
         '/etc/systemd/system/multi-user.target.wants/blueblue-udpgw@7200.service',
         '/etc/systemd/system/multi-user.target.wants/blueblue-udpgw@7300.service',
         '/usr/local/lib/blueblue', '/usr/local/bin/ws-stunnel', '/etc/init.d/stunnel5',
         '/etc/systemd/system/stunnel5.service', '/etc/systemd/system/ws-stunnel.service',
         '/etc/systemd/system/blueblue-expiry.service', '/etc/systemd/system/blueblue-expiry.timer',
         '/etc/systemd/system/blueblue-cert-watch.service', '/etc/systemd/system/blueblue-cert-watch.path',
         '/etc/systemd/system/multi-user.target.wants/blueblue-cert-watch.path',
         '/usr/local/share/xray', '/etc/cron.d', '/var/spool/cron/crontabs/root',
         '/etc/systemd/system/multi-user.target.wants/stunnel5.service',
         '/etc/systemd/system/multi-user.target.wants/ws-stunnel.service',
         '/etc/systemd/system/timers.target.wants/blueblue-expiry.timer'] + ['/usr/bin/' + c for c in COMMANDS]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['save', 'restore'])
    p.add_argument('directory', type=Path)
    p.add_argument('--extra', action='append', default=[])
    a = p.parse_args()
    if os.geteuid() != 0:
        raise SystemExit('Root required')
    if a.action == 'save':
        a.directory.mkdir(parents=True, exist_ok=False, mode=0o700)
        paths = list(dict.fromkeys(PATHS + a.extra))
        # Avoid overlapping archive entries, including a custom config inside /etc/xray.
        paths = [v for v in paths if not any(v.startswith(parent + '/') for parent in paths if parent != v)]
        missing = [s for s in paths if not os.path.lexists(s)]
        entries = []
        for name in paths:
            if os.path.lexists(name):
                entries.append(name)
                if Path(name).is_dir() and not Path(name).is_symlink():
                    for base, directories, files in os.walk(name, followlinks=False):
                        entries.extend(str(Path(base, leaf)) for leaf in directories + files)
        with tarfile.open(a.directory / 'files.tar.gz', 'w:gz', dereference=False) as tar:
            for source in paths:
                if os.path.lexists(source):
                    tar.add(source, arcname=source.lstrip('/'))
        attributes = {}
        for name in entries:
            attrs = {attr: base64.b64encode(os.getxattr(name, attr, follow_symlinks=False)).decode()
                     for attr in os.listxattr(name, follow_symlinks=False)
                     if attr.startswith('system.posix_acl_') or attr == 'security.capability'}
            if attrs:
                attributes[name] = attrs
        (a.directory / 'manifest.json').write_text(json.dumps({'paths': paths, 'missing': missing,
            'entries': entries, 'attributes': attributes}, indent=2))
        print(a.directory)
    else:
        manifest = json.loads((a.directory / 'manifest.json').read_text())
        # Operator invokes this only for this root-created snapshot; reject writable/untrusted backups.
        info = a.directory.stat()
        if info.st_uid != 0 or info.st_mode & 0o022:
            raise SystemExit('Snapshot directory must be root-owned and not group/world writable')
        expected = set(manifest.get('entries', []))
        for root in manifest['paths']:
            if Path(root).is_dir() and not Path(root).is_symlink() and root not in manifest['missing']:
                current = []
                for base, directories, files in os.walk(root, followlinks=False):
                    current.extend(Path(base, leaf) for leaf in directories + files)
                for target in sorted(current, key=lambda v: len(v.parts), reverse=True):
                    if str(target) not in expected:
                        if target.is_symlink() or target.is_file():
                            target.unlink()
                        elif target.is_dir():
                            target.rmdir()
        for target in manifest['missing']:
            if target not in manifest['paths'] or not target.startswith(('/etc/', '/usr/', '/var/', '/home/vps/')):
                raise SystemExit('Unsafe rollback path')
            path = Path(target)
            if path.is_symlink() or path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
        with tarfile.open(a.directory / 'files.tar.gz') as tar:
            for member in tar.getmembers():
                if member.name.startswith('/') or '..' in Path(member.name).parts:
                    raise SystemExit('Unsafe archive path')
            tar.extractall('/')  # Trusted local archive, preserves original symlinks/ownership/modes.
        for name, attrs in manifest.get('attributes', {}).items():
            for attr, value in attrs.items():
                os.setxattr(name, attr, base64.b64decode(value), follow_symlinks=False)


if __name__ == '__main__':
    main()
