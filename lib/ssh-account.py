#!/usr/bin/env python3
"""SSH identities use system account expiry, with a managed-user registry for safe deletion."""
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import pwd
import re
import subprocess
import sys
import getpass

REGISTRY = Path('/etc/blueblue/ssh-users.json')


def call(*args, **kwargs):
    return subprocess.run(args, check=True, text=True, **kwargs)


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else 'list'
    users = json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}
    today = dt.date.today()
    if action == 'sessions':
        call('ss', '-tnp')
        return
    if action == 'list':
        for name, expiry in sorted(users.items()):
            print(name, expiry)
        return
    if action == 'expire':
        for name, expiry in users.items():
            if expiry <= today.isoformat():
                # Expiry locks authentication without destroying a user's files or UID.
                call('usermod', '--lock', name)
                subprocess.run(['pkill', '-TERM', '-u', name], check=False)
        return
    name = sys.argv[2] if len(sys.argv) > 2 else input('Username: ').strip()
    if not re.fullmatch(r'[a-z_][a-z0-9_-]{0,31}', name):
        raise ValueError('Use a Linux username: lowercase letters, digits, underscore or hyphen')
    if action == 'add':
        try:
            pwd.getpwnam(name)
        except KeyError:
            pass
        else:
            raise ValueError('System user already exists')
        password = getpass.getpass('Password: ')
        if not password or '\n' in password or ':' in password:
            raise ValueError('Password must be nonempty without colon/newline')
        days = int(input('Expiry in days: '))
        if days < 1:
            raise ValueError('Days must be positive')
        expiry = (today + dt.timedelta(days=days)).isoformat()
        call('useradd', '--expiredate', expiry, '--shell', '/bin/false', '--no-create-home', name)
        try:
            call('chpasswd', input=name + ':' + password + '\n')
        except BaseException:
            call('userdel', name)
            raise
        users[name] = expiry
        print(f'SSH account {name}; expiry {expiry}. TLS 447/777; HTTP upgrade 80/443 after certificate setup.')
    else:
        if name not in users:
            # Adopt only an existing non-system account with /home and an explicit shadow expiry.
            account = pwd.getpwnam(name)
            if account.pw_uid < 1000 or account.pw_uid == 65534 or not account.pw_dir.startswith('/home/'):
                raise ValueError('Refusing to manage a system account')
            shadow = next(line.split(':') for line in Path('/etc/shadow').read_text().splitlines()
                          if line.split(':', 1)[0] == name)
            expires = int(shadow[7]) if shadow[7] else -1
            if expires < 0:
                raise ValueError('Legacy account has no expiry; use chage explicitly before adoption')
            users[name] = (dt.date(1970, 1, 1) + dt.timedelta(days=expires)).isoformat()
        if action == 'delete':
            call('userdel', name)
            del users[name]
        elif action == 'renew':
            days = int(input('Extend by days: '))
            if days < 1:
                raise ValueError('Days must be positive')
            expiry = (max(today, dt.date.fromisoformat(users[name])) + dt.timedelta(days=days)).isoformat()
            call('chage', '-E', expiry, name)
            call('usermod', '--unlock', name)
            users[name] = expiry
        else:
            raise ValueError('Use add, list, renew, delete or expire')
    REGISTRY.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = REGISTRY.with_suffix('.new')
    temp.write_text(json.dumps(users, indent=2) + '\n')
    temp.chmod(0o600)
    os.replace(temp, REGISTRY)


if __name__ == '__main__':
    if os.geteuid() != 0:
        sys.exit('Root required')
    with open('/run/lock/blueblue-ssh.lock', 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        main()
