#!/usr/bin/env python3
"""Local, private backups. Optional uploads require an operator-selected rclone remote."""
import argparse
import datetime as dt
import fcntl
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
sys.path.insert(0, '/usr/local/lib/blueblue')
if not os.environ.get('XRAY_CONFIG') and Path('/etc/blueblue/settings.json').exists():
    os.environ['XRAY_CONFIG'] = json.loads(Path('/etc/blueblue/settings.json').read_text())['config']
from blueblue import CONFIG, DB, STATE, SETTINGS, atomic, encoded, load, transaction

ROOTS = ['etc/xray', 'usr/local/etc/xray', 'etc/blueblue', 'etc/nginx', 'etc/stunnel5',
         'root/.acme.sh', 'etc/letsencrypt', 'home/vps/public_html', 'etc/cron.d',
         'var/spool/cron/crontabs/root', 'var/lib/scrz-prem']


def create(directory):
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    archive = directory / ('blueblue-' + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + str(os.getpid()) + '.tar.gz')
    config, db, settings = load()
    with tarfile.open(archive, 'x:gz', dereference=True) as tar:
        custom = [str(CONFIG).lstrip('/'), settings['certificate'].lstrip('/'), settings['private_key'].lstrip('/')]
        roots = ROOTS + [c for c in custom if c not in ROOTS and not any(c.startswith(r + '/') for r in ROOTS)]
        for name in roots:
            path = Path('/' + name)
            if path.exists():
                tar.add(path, arcname=name)
        payload = encoded({'config': config, 'accounts': db, 'settings': settings}).encode()
        info = tarfile.TarInfo('blueblue-account-state.json')
        info.size, info.mode = len(payload), 0o600
        tar.addfile(info, io.BytesIO(payload))
        # Preserve SSH hashes for recovery without replacing whole system account databases.
        names = set(json.loads((STATE / 'ssh-users.json').read_text())) if (STATE / 'ssh-users.json').exists() else set()
        import pwd
        shadow = {line.split(':')[0]: line.split(':') for line in Path('/etc/shadow').read_text().splitlines()}
        records = []
        for entry in pwd.getpwall():
            if entry.pw_uid >= 1000 and entry.pw_uid != 65534 and entry.pw_dir.startswith('/home/'):
                fields = shadow.get(entry.pw_name)
                if fields and (entry.pw_name in names or fields[7]):
                    records.append({'name': entry.pw_name, 'hash': fields[1], 'expiry': fields[7],
                                    'shell': entry.pw_shell, 'home': entry.pw_dir})
        payload = encoded(records).encode()
        info = tarfile.TarInfo('blueblue-ssh-accounts.json')
        info.size, info.mode = len(payload), 0o600
        tar.addfile(info, io.BytesIO(payload))
    archive.chmod(0o600)
    print(archive)
    destination = os.environ.get('BLUEBLUE_BACKUP_DEST')
    if destination:
        # Configuration is explicit; no embedded credentials, public links or default destination.
        subprocess.run(['rclone', 'copy', str(archive), destination], check=True)
    return archive


def restore(args):
    # Always make a recovery point before changing account data.
    create(Path('/var/backups/blueblue/before-restore'))
    with tarfile.open(args.archive, 'r:gz') as tar:
        for member in tar.getmembers():
            if member.name.startswith('/') or '..' in Path(member.name).parts or member.issym() or member.islnk():
                raise ValueError('Unsafe archive member; restore only Blueblue-created backups')
        data = json.load(tar.extractfile('blueblue-account-state.json'))
        config, db, settings = load()
        # Account recovery keeps current listeners, domain, certificates, API and routing.
        db = data['accounts']
        source = data['config']
        for inbound in config['inbounds']:
            proto = inbound.get('protocol')
            if proto not in db['accounts']:
                continue
            net = inbound.get('streamSettings', {}).get('network', 'raw')
            original = next((i for i in source['inbounds'] if i.get('protocol') == proto and
                             i.get('streamSettings', {}).get('network', 'raw') == net), None)
            if original:
                key = 'accounts' if proto == 'socks' else 'clients'
                inbound['settings'][key] = original.get('settings', {}).get(key, [])
        if args.restore_config:
            config = source
        transaction(config, db, settings)
        if args.restore_ssh:
            import pwd
            records = json.load(tar.extractfile('blueblue-ssh-accounts.json'))
            for record in records:
                name = record['name']
                if not __import__('re').fullmatch(r'[a-z_][a-z0-9_-]{0,31}', name):
                    raise ValueError('Unsafe SSH username')
                try:
                    pwd.getpwnam(name)
                except KeyError:
                    subprocess.run(['useradd', '-M', '-s', record['shell'], name], check=True)
                else:
                    raise ValueError(f'SSH user {name} already exists; refusing to replace its password')
                subprocess.run(['chpasswd', '-e'], input=name + ':' + record['hash'] + '\n', text=True, check=True)
                if record['expiry']:
                    subprocess.run(['chage', '-E', record['expiry'], name], check=True)
    print('Accounts restored. Existing domain, certificate paths and renewal jobs preserved.')


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='action', required=True)
    a = sub.add_parser('create')
    a.add_argument('--directory', type=Path, default=Path('/var/backups/blueblue/accounts'))
    a = sub.add_parser('restore')
    a.add_argument('archive', type=Path)
    a.add_argument('--restore-config', action='store_true', help='Also replace transport/routing configuration')
    a.add_argument('--restore-ssh', action='store_true', help='Create missing SSH accounts; refuses existing usernames')
    args = p.parse_args()
    if os.geteuid() != 0:
        sys.exit('Root required')
    with open('/run/lock/blueblue.lock', 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if args.action == 'create':
            create(args.directory)
        else:
            restore(args)


if __name__ == '__main__':
    main()
