#!/usr/bin/env python3
import fcntl
import os
from pathlib import Path
import pwd
import re
import sys
from blueblue import STATE, SETTINGS, atomic, encoded, read_json, domain_name, nginx_nodes, https_server, run


def main():
    action = sys.argv[1]
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    settings = read_json(SETTINGS, {})
    if action == 'set':
        domain = domain_name(sys.argv[2])
        site = Path(settings['nginx'])
        text = site.read_text()
        original = text
        if settings.get('fresh_site'):
            node = next(n for n in nginx_nodes(text) if n['args'] == ['server'])
        else:
            _, _, node, _, _ = https_server(settings.get('domain', domain), str(site))
        names = next((n for n in node['children'] if n['args'][:1] == ['server_name']), None)
        if names:
            aliases = [n for n in names['args'][1:] if n != '_']
            if domain not in aliases:
                aliases.append(domain)
            text = text[:names['start']] + 'server_name ' + ' '.join(aliases) + ';' + text[names['end']:]
        else:
            text = text[:node['open']] + '\n    server_name ' + domain + ';' + text[node['open']:]
        atomic(site, text)
        try:
            run('nginx', '-t')
            run('systemctl', 'reload-or-restart', 'nginx')
        except BaseException:
            atomic(site, original)
            raise
        settings['domain'] = domain
        atomic(SETTINGS, encoded(settings))
        atomic(Path('/etc/xray/domain'), domain + '\n', 0o644)
        atomic(Path('/var/lib/scrz-prem/ipvps.conf'), 'IP=' + domain + '\n', 0o600)
        atomic(Path('/root/domain'), domain + '\n')
    elif action == 'info':
        domain = domain_name(settings.get('domain') or Path('/etc/xray/domain').read_text().strip())
        print(domain)
        print(settings.get('certificate', '/etc/xray/xray.crt'))
        print(settings.get('private_key', '/etc/xray/xray.key'))
    elif action == 'activate':
        cert, key = Path(settings['certificate']), Path(settings['private_key'])
        if not cert.is_file() or not key.is_file():
            raise ValueError('Certificate issuance did not produce both files')
        from stunnel import grant
        user = 'www-data'
        service = settings.get('service', 'xray.service')
        try:
            user = run('systemctl', 'show', service, '-p', 'User', '--value', capture=True).strip() or 'root'
        except Exception:
            pass
        if user != 'root':
            grant(cert, user)
            grant(key, user)
        if settings.get('fresh_site'):
            path = Path(settings['nginx'])
            text = path.read_text()
            original = text
            if 'listen 443 ssl http2;' not in text:
                text = text.replace('    listen 80;', '    listen 80;\n    listen 443 ssl http2;\n'
                    + f'    ssl_certificate {cert};\n    ssl_certificate_key {key};\n'
                    + '    ssl_protocols TLSv1.2 TLSv1.3;', 1)
            atomic(path, text)
            try:
                run('nginx', '-t')
            except BaseException:
                atomic(path, original)
                raise
    elif action == 'deploy':
        lineage = Path(sys.argv[2]).resolve(strict=True)
        if lineage != Path('/etc/letsencrypt/live', settings['domain']).resolve(strict=True):
            return
        atomic(Path(settings['certificate']), (lineage / 'fullchain.pem').read_bytes(), 0o644)
        atomic(Path(settings['private_key']), (lineage / 'privkey.pem').read_bytes())
        from stunnel import grant
        service_user = run('systemctl', 'show', settings.get('service', 'xray.service'),
                           '-p', 'User', '--value', capture=True).strip() or 'root'
        for user in set(('www-data', 'stunnel4', service_user)) - {'root'}:
            try:
                pwd.getpwnam(user)
                grant(settings['certificate'], user)
                grant(settings['private_key'], user)
            except KeyError:
                pass
        run('nginx', '-t')
        run('systemctl', 'reload', 'nginx')
        run('systemctl', 'reload-or-restart', 'stunnel5')
        run('systemctl', 'restart', settings.get('service', 'xray.service'))


if __name__ == '__main__':
    if os.geteuid() != 0:
        sys.exit('Root required')
    with open('/run/lock/blueblue.lock', 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        main()
