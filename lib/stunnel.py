#!/usr/bin/env python3
"""Migrate the legacy stunnel5 instance to the distribution's OpenSSL-linked package."""
import argparse
import os
from pathlib import Path
import pwd
import re
import shutil
import subprocess
import sys
from blueblue import STATE, atomic, read_json, SETTINGS, run


def grant(path, username):
    path = Path(path).resolve(strict=True)
    for parent in reversed(path.parents):
        if str(parent) != '/':
            run('setfacl', '-m', f'u:{username}:--x', str(parent))
    run('setfacl', '-m', f'u:{username}:r--', str(path))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fresh', action='store_true')
    parser.add_argument('--stage', action='store_true')
    args = parser.parse_args()
    if os.geteuid() != 0:
        sys.exit('Root required')
    target = Path('/etc/stunnel5/stunnel5.conf')
    settings = read_json(SETTINGS, {})
    other = [p for p in Path('/etc/stunnel').glob('*.conf')
             if re.search(r'^\s*\[', p.read_text(), re.M)]
    if other:
        raise ValueError('Other package Stunnel configurations found: ' + ','.join(map(str, other)))
    if target.exists():
        text = target.read_text()
    elif args.fresh:
        text = f'''cert = {settings['certificate']}
key = {settings['private_key']}
[dropbear]
accept = 447
connect = 127.0.0.1:109
[openssh]
accept = 777
connect = 127.0.0.1:22
'''
    else:
        # No competing daemon is adopted automatically.
        raise ValueError('Legacy /etc/stunnel5/stunnel5.conf absent; set up Stunnel separately')
    user = 'stunnel4'
    try:
        pwd.getpwnam(user)
    except KeyError:
        run('useradd', '--system', '--no-create-home', '--shell', '/usr/sbin/nologin', user)
    globals_, sections = text.split('[', 1) if '[' in text else (text, '')
    if not sections:
        raise ValueError('No Stunnel service sections found')
    # Remove daemonization/chroot/privilege directives handled by systemd. Keep every service mapping.
    globals_ = re.sub(r'^\s*(?:foreground|pid|output|syslog|chroot|setuid|setgid|sslVersion|sslVersionMin|sslVersionMax|fips|options)\s*=.*$',
                      '', globals_, flags=re.M | re.I)
    text = 'foreground = yes\npid =\nsyslog = yes\nsslVersionMin = TLSv1.2\n' + globals_ + '[' + sections
    # Legacy per-section TLS1 / SSLv3 overrides must not defeat the global minimum.
    text = re.sub(r'^\s*sslVersion\s*=.*$', '', text, flags=re.M | re.I)
    text = re.sub(r'^\s*sslVersionMin\s*=.*$', 'sslVersionMin = TLSv1.2', text, flags=re.M | re.I)
    for key in ('cert', 'key'):
        for filename in re.findall(r'^\s*' + key + r'\s*=\s*(\S+)\s*$', text, re.M | re.I):
            if Path(filename).exists():
                if key == 'key' and Path(filename).resolve() == Path('/etc/xray/xray.key'):
                    # Repair the legacy nobody-owned/world-readable project key, keeping its bytes/path.
                    run('chown', 'root:root', filename)
                    os.chmod(filename, 0o600)
                    xray_user = run('systemctl', 'show', settings.get('service', 'xray.service'),
                                    '-p', 'User', '--value', capture=True).strip() or 'root'
                    if xray_user != 'root':
                        grant(filename, xray_user)
                grant(filename, user)
            elif not args.fresh:
                raise ValueError('Missing Stunnel certificate/key: ' + filename)
    target.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(target.parent, 0o750)  # Original installer used 0644 on a directory: no traversal.
    run('chown', 'root:stunnel4', str(target.parent))
    atomic(target, text, 0o640)
    run('chown', 'root:stunnel4', str(target))
    os.chmod(target, 0o640)
    unit = '''[Unit]
Description=Blueblue SSH over TLS (distribution Stunnel)
After=network.target ssh.service dropbear.service
ConditionPathExists=/etc/xray/xray.crt
[Service]
Type=simple
User=stunnel4
Group=stunnel4
ExecStart=/usr/bin/stunnel4 /etc/stunnel5/stunnel5.conf
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
AmbientCapabilities=CAP_NET_BIND_SERVICE
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
RuntimeDirectory=blueblue-stunnel
UMask=0077
[Install]
WantedBy=multi-user.target
'''
    # Certificate conditions must follow the actual pre-existing path, including custom installations.
    certs = re.findall(r'^\s*cert\s*=\s*(\S+)', text, re.M | re.I)
    if certs:
        unit = unit.replace('/etc/xray/xray.crt', certs[0])
    oldinit = Path('/etc/init.d/stunnel5')
    if not args.stage:
        subprocess.run(['systemctl', 'stop', 'stunnel5.service'], check=False)
    if oldinit.exists():
        archive = STATE / ('legacy-stunnel5.init.' + str(os.getpid()))
        shutil.move(str(oldinit), archive)
    atomic(Path('/etc/systemd/system/stunnel5.service'), unit, 0o644)
    bridge = Path('/usr/local/bin/ws-stunnel')
    atomic(bridge, Path(__file__).with_name('ws_bridge.py').read_text(), 0o755)
    os.chmod(bridge, 0o755)
    atomic(Path('/etc/systemd/system/ws-stunnel.service'), '''[Unit]
Description=Blueblue SSH HTTP upgrade bridge (Python 3)
After=network.target dropbear.service
[Service]
User=nobody
Group=nogroup
ExecStart=/usr/bin/python3 /usr/local/bin/ws-stunnel
EnvironmentFile=-/etc/blueblue/bridge.env
Restart=on-failure
RestartSec=3
AmbientCapabilities=CAP_NET_BIND_SERVICE
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
UMask=0077
[Install]
WantedBy=multi-user.target
''', 0o644)
    if not args.stage:
        run('systemctl', 'daemon-reload')
        run('systemctl', 'enable', 'stunnel5', 'ws-stunnel')
        if all(Path(p).exists() for p in certs):
            run('systemctl', 'restart', 'stunnel5')
        run('systemctl', 'restart', 'ws-stunnel')


if __name__ == '__main__':
    main()
