#!/usr/bin/env python3
"""Reload consumers of renewed certificates without changing or invoking ACME jobs."""
import fcntl
import json
from pathlib import Path
import pwd
from blueblue import SETTINGS, run, strip_comments
from stunnel import grant


def main():
    settings = json.loads(SETTINGS.read_text())
    cert, key = settings['certificate'], settings['private_key']
    public_cert = run('openssl', 'x509', '-in', cert, '-pubkey', '-noout', capture=True)
    public_key = run('openssl', 'pkey', '-in', key, '-pubout', capture=True)
    if public_cert.strip() != public_key.strip():
        raise ValueError('Renewed certificate and key do not match; services kept running')
    service_user = run('systemctl', 'show', settings.get('service', 'xray.service'),
                       '-p', 'User', '--value', capture=True).strip() or 'root'
    for user in {'stunnel4', service_user} - {'root'}:
        try:
            pwd.getpwnam(user)
        except KeyError:
            continue
        grant(cert, user)
        grant(key, user)
    run('nginx', '-t')
    run('systemctl', 'reload', 'nginx')
    run('systemctl', 'reload-or-restart', 'stunnel5')
    config = json.loads(strip_comments(Path(settings['config']).read_text()))
    if any(i.get('streamSettings', {}).get('security') == 'tls' for i in config['inbounds']):
        run('systemctl', 'restart', settings.get('service', 'xray.service'))


if __name__ == '__main__':
    with open('/run/lock/blueblue.lock', 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        main()
