#!/usr/bin/env python3
"""Blueblue configuration and account transactions. Python standard library only.

Legacy Blueblue by NevermoreSSH (2022); modernization for reaganchomba/blueblue.
"""
import argparse
import copy
import datetime as dt
import fcntl
import glob
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import uuid
import zipfile
from contextlib import nullcontext

STATE = Path('/etc/blueblue')
CONFIG = Path(os.environ.get('XRAY_CONFIG', '/etc/xray/config.json'))
DB = STATE / 'accounts.json'
SETTINGS = STATE / 'settings.json'
TODAY = dt.date.today


def run(*args, capture=False):
    return subprocess.run(args, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None).stdout


def atomic(path, data, mode=0o600):
    path = Path(path)
    if path.is_symlink():
        path = path.resolve(strict=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    old = path.stat() if path.exists() else None
    fd, name = tempfile.mkstemp(prefix='.blueblue-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(data.encode() if isinstance(data, str) else data)
            out.flush()
            os.fsync(out.fileno())
        os.chmod(name, stat.S_IMODE(old.st_mode) if old else mode)
        if old:
            os.chown(name, old.st_uid, old.st_gid)
            for attr in os.listxattr(path):
                if attr.startswith('system.posix_acl_'):
                    os.setxattr(name, attr, os.getxattr(path, attr))
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def encoded(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False) + '\n'


def read_json(path, default=None):
    return json.loads(path.read_text()) if path.exists() else copy.deepcopy(default)


def strip_comments(text):
    # Preserve quoted URLs, escaped quotes, line positions and JSON structure.
    pattern = r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*[\s\S]*?\*/|^[ \t]*\#[^\n]*'
    return re.sub(pattern, lambda m: m[0] if m[0].startswith('"') else
                  ''.join('\n' if c == '\n' else ' ' for c in m[0]), text, flags=re.M)


def network(inbound):
    return inbound.get('streamSettings', {}).get('network', 'raw')


def accounts_load(text, config):
    db = read_json(DB, {'schema': 1, 'accounts': {}})
    markers = {'vls': 'vless', 'vlsg': 'vless', 'vms': 'vmess', 'vmsg': 'vmess',
               'tr': 'trojan', 'trg': 'trojan', 'ssw': 'shadowsocks', 'sswg': 'shadowsocks',
               'ss': 'socks', 'ssg': 'socks'}
    expiry = {}
    for marker, name, date in re.findall(r'^\s*#(\w+)\s+(\S+)\s+(\d{4}-\d{2}-\d{2})\s*$', text, re.M):
        if marker in markers:
            dt.date.fromisoformat(date)
            key = (markers[marker], name)
            # Earliest expiry wins if legacy transport metadata disagrees.
            expiry[key] = min(expiry.get(key, date), date)
    for inbound in config.get('inbounds', []):
        proto = inbound.get('protocol')
        if proto not in ('vless', 'vmess', 'trojan', 'shadowsocks', 'socks'):
            continue
        users = db['accounts'].setdefault(proto, {})
        clients = inbound.get('settings', {}).get('clients', [])
        if proto == 'socks':
            clients = inbound.get('settings', {}).get('accounts', [])
        for client in clients:
            name = client.get('email') or client.get('user')
            if not name:
                continue  # Anonymous legacy credentials remain in their original inbounds.
            record = users.setdefault(name, {'client': copy.deepcopy(client),
                                             'expiry': expiry.get((proto, name)), 'transports': []})
            for key in ('id', 'password', 'pass'):
                if key in client and record['client'].get(key) != client[key]:
                    raise ValueError(f'Conflicting {proto} credentials for {name}; reconcile before migration')
            if record.get('expiry') is None and (proto, name) in expiry:
                record['expiry'] = expiry[proto, name]
            if network(inbound) not in record['transports']:
                record['transports'].append(network(inbound))
    for proto, users in db['accounts'].items():
        owners = {}
        for name, record in users.items():
            if record.get('deleted'):
                continue
            client = record['client']
            identity = client.get('id', client.get('password', client.get('user')))
            if identity in owners and owners[identity] != name:
                raise ValueError(f'{proto} credential shared by multiple usernames; reconcile before migration')
            owners[identity] = name
    return db


def load():
    text = CONFIG.read_text()
    config = json.loads(strip_comments(text))
    return config, accounts_load(text, config), read_json(SETTINGS, {})


def valid_name(name):
    if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}', name):
        raise ValueError('Use 1-64 letters, digits, underscore, dot or hyphen')
    return name


def domain_name(domain):
    domain = domain.strip().lower().encode('idna').decode()
    if len(domain) > 253 or '.' not in domain or not all(
            re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label) for label in domain.split('.')):
        raise ValueError('A fully qualified DNS domain is required')
    return domain


def sync(config, db):
    for inbound in config['inbounds']:
        proto = inbound.get('protocol')
        users = db['accounts'].get(proto, {})
        if not users:
            continue
        key = 'accounts' if proto == 'socks' else 'clients'
        clients = inbound.setdefault('settings', {}).setdefault(key, [])
        identities = {r['client'].get('id', r['client'].get('password', r['client'].get('user')))
                      for r in users.values()}
        clients[:] = [c for c in clients if (c.get('email') or c.get('user')) not in users
                      and c.get('id', c.get('password', c.get('user'))) not in identities]
        for name, record in users.items():
            if record.get('expiry') and record['expiry'] <= TODAY().isoformat():
                continue
            if network(inbound) in record['transports']:
                client = copy.deepcopy(record['client'])
                if network(inbound) not in ('raw', 'tcp'):
                    client.pop('flow', None)
                clients.append(client)


def transaction(config, db, settings, extra=None, restart=True):
    sync(config, db)
    files = {CONFIG: encoded(config), DB: encoded(db), SETTINGS: encoded(settings)}
    files.update(extra or {})
    before = {p: (p.read_bytes() if p.exists() else None) for p in files}
    changed = [p for p, value in files.items() if before[p] != value.encode()]
    if not changed:
        return
    try:
        for p in changed:
            atomic(p, files[p], 0o640 if p == CONFIG else 0o600)
        if restart:
            # Deployment-time guards. These are not executed during repository development.
            binary = settings.get('binary', '/usr/local/bin/xray')
            run(binary, 'run', '-test', '-config', str(CONFIG))
            if any(str(p).startswith('/etc/nginx/') for p in changed):
                run('nginx', '-t')
            run('systemctl', 'restart', settings.get('service', 'xray.service'))
            if any(str(p).startswith('/etc/nginx/') for p in changed):
                run('systemctl', 'reload', 'nginx')
    except BaseException:
        for p in changed:
            if before[p] is None:
                p.unlink(missing_ok=True)
            else:
                atomic(p, before[p])
        if restart:
            subprocess.run(['systemctl', 'restart', settings.get('service', 'xray.service')])
            subprocess.run(['systemctl', 'reload', 'nginx'])
        raise


# Nginx token tree: edits are limited to the selected server's byte spans.
TOKEN = re.compile(r'\s+|\#[^\n]*|"(?:\\.|[^"\\])*"|\x27(?:\\.|[^\x27\\])*\x27|\$\{[^}]*\}|[{};]|[^\s{};\#"\x27]+')


def nginx_nodes(text):
    tokens = [(m[0], m.start(), m.end()) for m in TOKEN.finditer(text)
              if not m[0].isspace() and not m[0].startswith('#')]
    root = {'children': [], 'args': [], 'start': 0, 'end': len(text)}
    stack, args, start = [root], [], 0
    for value, a, b in tokens:
        if value == '{':
            node = {'args': args, 'start': start, 'open': b, 'children': []}
            stack[-1]['children'].append(node)
            stack.append(node)
            args = []
        elif value == '}':
            if len(stack) == 1 or args:
                raise ValueError('Unsupported Nginx syntax; no edits made')
            stack.pop().update(close=a, end=b)
        elif value == ';':
            stack[-1]['children'].append({'args': args, 'start': start, 'end': b})
            args = []
        else:
            if not args:
                start = a
            args.append(value.strip('"\x27'))
    if len(stack) != 1:
        raise ValueError('Unbalanced Nginx blocks')
    return root['children']


def nginx_files(path=Path('/etc/nginx/nginx.conf'), seen=None):
    seen = set() if seen is None else seen
    path = path.resolve()
    if path in seen:
        return
    seen.add(path)
    text = path.read_text()
    yield path, text
    def walk(nodes):
        for node in nodes:
            args = node['args']
            if args and args[0] == 'include':
                pattern = args[1]
                if not pattern.startswith('/'):
                    pattern = '/etc/nginx/' + pattern
                for name in sorted(glob.glob(pattern)):
                    yield from nginx_files(Path(name), seen)
            yield from walk(node.get('children', []))
    yield from walk(nginx_nodes(text))


def directives(server, key):
    return [n['args'][1:] for n in server['children'] if n['args'] and n['args'][0] == key]


def https_server(domain, override=None):
    candidates = []
    for path, text in nginx_files():
        def walk(nodes):
            for node in nodes:
                if node['args'] == ['server']:
                    listens = directives(node, 'listen')
                    if any('ssl' in x and any(re.search(r'(?:^|:)443$', t) for t in x) for x in listens):
                        if override is None or path == Path(override).resolve():
                            candidates.append((path, text, node))
                yield from walk(node.get('children', []))
            return
        list(walk(nginx_nodes(text)))
    matches = [c for c in candidates if domain in sum(directives(c[2], 'server_name'), [])]
    choices = matches or candidates
    if len(choices) != 1:
        raise ValueError('HTTPS server is ambiguous or absent; set NGINX_CONFIG and BLUEBLUE_DOMAIN explicitly')
    path, text, node = choices[0]
    certs, keys = directives(node, 'ssl_certificate'), directives(node, 'ssl_certificate_key')
    if len(certs) != 1 or len(keys) != 1 or '$' in certs[0][0] + keys[0][0]:
        raise ValueError('Use one explicit certificate/key pair in the selected server block')
    return path, text, node, certs[0][0], keys[0][0]


def route(net, path, port):
    if net in ('xhttp', 'grpc'):
        return f'''    location ^~ {path} {{
        client_max_body_size 0;
        client_body_timeout 5m;
        grpc_read_timeout 315s;
        grpc_send_timeout 5m;
        grpc_set_header Host $host;
        grpc_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        grpc_pass grpc://127.0.0.1:{port};
    }}\n'''
    return f'''    location {'=' if net == 'ws' else '^~'} {path} {{
        proxy_pass http://127.0.0.1:{port};
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 5m;
        proxy_buffering off;
    }}\n'''


def add_routes(text, node, additions):
    segment = text[node['open']:node['close']]
    for net, endpoint, port in additions:
        label = f'BLUEBLUE {net}'
        pattern = r'\n[ \t]*# BEGIN ' + label + r'\n[\s\S]*?# END ' + label + r'\n'
        segment = re.sub(pattern, '\n', segment)
        for child in nginx_nodes('server {' + segment + '}')[0]['children']:
            if child['args'][:1] == ['location']:
                existing = child['args'][-1]
                if existing == endpoint or (net == 'xhttp' and existing.rstrip('/') == endpoint.rstrip('/')):
                    raise ValueError(f'Existing unmanaged location {endpoint}; reconcile explicitly')
        segment = segment.rstrip() + f'\n\n    # BEGIN {label}\n' + route(net, endpoint, port) + f'    # END {label}\n'
    # Old and distro Nginx support listen ... http2; do not introduce `http2 on` or QUIC.
    listens = directives(node, 'listen')
    if not directives(node, 'http2') and not any('http2' in x for x in listens):
        segment = re.sub(r'(listen\s+[^;]*\b443\b[^;]*\bssl)([^;]*);', r'\1 http2\2;', segment)
    return text[:node['open']] + segment + text[node['close']:]


def free_port(config, preferred, udp=False):
    used = {int(i['port']) for i in config['inbounds'] if str(i.get('port', '')).isdigit()}
    port = int(preferred)
    if not 1024 <= port <= 65535:
        raise ValueError('Choose an unprivileged port between 1024 and 65535')
    if port in used:
        raise ValueError(f'Configured port {port} is already used by an inbound')
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM if udp else socket.SOCK_STREAM) as sock:
        sock.bind(('0.0.0.0', port))
    return port


def inbound(net, port, path=None, proto='vless'):
    setting = {'ws': 'wsSettings', 'grpc': 'grpcSettings', 'xhttp': 'xhttpSettings',
               'httpupgrade': 'httpupgradeSettings', 'kcp': 'kcpSettings', 'raw': 'rawSettings'}[net]
    value = {'serviceName': path} if net == 'grpc' else ({'path': path} if path else {})
    if net == 'xhttp':
        value['mode'] = 'auto'
    return {'tag': f'blueblue-{proto}-{net}', 'listen': '127.0.0.1', 'port': port,
            'protocol': proto, 'settings': {'clients': [], **({'decryption': 'none'} if proto == 'vless' else {})},
            'streamSettings': {'network': net, 'security': 'none', setting: value}}


def migrate(args):
    config, db, settings = load()
    domain = domain_name(os.environ.get('BLUEBLUE_DOMAIN') or settings.get('domain') or
                         Path('/etc/xray/domain').read_text().strip())
    path, text, node, cert, key = https_server(domain, os.environ.get('NGINX_CONFIG'))
    settings.update(domain=domain, certificate=cert, private_key=key, nginx=str(path),
                    binary=os.environ.get('XRAY_BINARY', settings.get('binary', '/usr/local/bin/xray')),
                    service=os.environ.get('XRAY_SERVICE', settings.get('service', 'xray.service')),
                    config=str(CONFIG), tls_port=443)
    if any(any(re.search(r'(?:^|:)80$', t) for t in listen) for listen in directives(node, 'listen')):
        settings['ws_http_port'] = 80
    if 'legacy_download' not in settings:
        settings['legacy_download'] = any(
            '/home/vps/public_html' in contents and re.search(r'listen\s+81\s*;', contents)
            for _, contents in nginx_files())
    additions = []
    nets = ['xhttp'] + (['httpupgrade'] if args.httpupgrade else [])
    for net in nets:
        matches = [i for i in config['inbounds'] if i.get('protocol') == 'vless' and network(i) == net]
        if len(matches) > 1:
            raise ValueError(f'Multiple VLESS/{net} inbounds; reconcile before migration')
        if matches:
            entry = matches[0]
            if entry.get('listen') != '127.0.0.1' or entry.get('streamSettings', {}).get('security', 'none') != 'none':
                raise ValueError(f'{net} already exists with a different architecture')
        else:
            endpoint = os.environ.get('XHTTP_PATH', '/xhttp/') if net == 'xhttp' else '/httpupgrade'
            if not re.fullmatch(r'/[A-Za-z0-9_/-]+', endpoint) or endpoint == '/':
                raise ValueError('Transport path must be a non-root safe URL path')
            if net == 'xhttp':
                endpoint = endpoint.rstrip('/') + '/'
            port = free_port(config, os.environ.get('XHTTP_PORT', 10086) if net == 'xhttp' else 10087)
            entry = inbound(net, port, endpoint)
            # Include anonymous legacy VLESS credentials, deduplicated by UUID.
            clients = {}
            for old in config['inbounds']:
                if old.get('protocol') == 'vless':
                    for client in old.get('settings', {}).get('clients', []):
                        c = copy.deepcopy(client)
                        c.pop('flow', None)
                        clients[c['id']] = c
            entry['settings']['clients'] = list(clients.values())
            config['inbounds'].append(entry)
        endpoint = entry['streamSettings'][net + 'Settings']['path']
        for record in db['accounts'].get('vless', {}).values():
            if (not matches or not DB.exists()) and net not in record['transports']:
                record['transports'].append(net)
        additions.append((net, endpoint, entry['port']))
    updated = add_routes(text, node, additions)
    transaction(config, db, settings, {path: updated}, restart=not args.stage)
    print(encoded(settings))


def exports(config, db, settings, proto, user):
    record = db['accounts'][proto][user]
    domain = settings.get('domain') or Path('/etc/xray/domain').read_text().strip()
    result, clients = [], {}
    for i in config['inbounds']:
        net = network(i)
        if i.get('protocol') != proto or net not in record['transports']:
            continue
        stream = copy.deepcopy(i.get('streamSettings', {}))
        local = i.get('listen') in ('127.0.0.1', '::1')
        port = settings.get('tls_port', 443) if local else int(i['port'])
        address = domain if local else settings.get('direct_addresses', {}).get(net, domain)
        if local:
            stream.update(security='tls', tlsSettings={'serverName': domain, 'allowInsecure': False})
            if net in ('grpc', 'xhttp'):
                stream['tlsSettings']['alpn'] = ['h2']
        elif stream.get('security') == 'tls':
            stream['tlsSettings'] = {'serverName': domain, 'allowInsecure': False}
        client = copy.deepcopy(record['client'])
        client.pop('email', None)
        if proto == 'vless':
            client['encryption'] = 'none'
        if net not in ('raw', 'tcp'):
            client.pop('flow', None)
        if proto in ('vless', 'vmess'):
            server = {'address': address, 'port': port, 'users': [client]}
            outbound_settings = {'vnext': [server]}
        elif proto == 'socks':
            server = {'address': address, 'port': port, 'users': [client]}
            outbound_settings = {'servers': [server]}
        else:
            server = {'address': address, 'port': port, **client}
            outbound_settings = {'servers': [server]}
        outbound = {'tag': 'proxy', 'protocol': proto, 'settings': outbound_settings,
                    'streamSettings': stream, 'mux': {'enabled': False}}
        clients[net] = {'inbounds': [{'listen': '127.0.0.1', 'port': 10808, 'protocol': 'socks',
                                    'settings': {'udp': True}}], 'outbounds': [outbound]}
        if net == 'ws' and local and settings.get('ws_http_port'):
            plain = copy.deepcopy(clients[net])
            plain_outbound = plain['outbounds'][0]
            plain_outbound['streamSettings']['security'] = 'none'
            plain_outbound['streamSettings'].pop('tlsSettings', None)
            targets = plain_outbound['settings'].get('vnext', plain_outbound['settings'].get('servers'))
            targets[0]['port'] = settings['ws_http_port']
            clients['ws-notls'] = plain
        if proto != 'vless':
            continue
        query = {'encryption': 'none', 'type': 'tcp' if net == 'raw' else net,
                 'security': stream.get('security', 'none')}
        if query['security'] == 'tls':
            query['sni'] = domain
        if net in ('ws', 'httpupgrade', 'xhttp'):
            query.update(host=domain, path=stream[net + 'Settings']['path'])
        if net == 'xhttp':
            query.update(mode='auto', alpn='h2')
        if net == 'grpc':
            query.update(serviceName=stream['grpcSettings']['serviceName'], mode='gun', alpn='h2')
        if net == 'kcp':
            query.update(seed=stream['kcpSettings']['seed'], headerType='none')
        if net == 'raw':
            query['headerType'] = 'none'
        uri_address = '[' + address + ']' if ':' in address else address
        result.append(f'vless://{client["id"]}@{uri_address}:{port}?' + urllib.parse.urlencode(query, quote_via=urllib.parse.quote)
                      + '#' + urllib.parse.quote(user + '-' + net))
        if net == 'ws' and local and settings.get('ws_http_port'):
            plain_query = {k: v for k, v in query.items() if k not in ('sni', 'alpn')}
            plain_query['security'] = 'none'
            result.append(f'vless://{client["id"]}@{uri_address}:{settings["ws_http_port"]}?'
                          + urllib.parse.urlencode(plain_query, quote_via=urllib.parse.quote)
                          + '#' + urllib.parse.quote(user + '-ws-notls'))
    content = f'Blueblue {proto}: {user}\nExpiry: {record.get("expiry")}\n' + '\n'.join(result) + '\n'
    directory = STATE / 'exports' / proto / valid_name(user)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    atomic(directory / 'links.txt', content)
    for net, client in clients.items():
        atomic(directory / (net + '.json'), encoded(client))
    if settings.get('legacy_download') and proto == 'vless':
        legacy = Path('/home/vps/public_html') / ('vless-' + user + '.txt')
        atomic(legacy, content, 0o644)
        os.chmod(legacy, 0o644)
        print(f'Legacy download (contains credentials): http://{domain}:81/vless-{user}.txt')
    # A shared secret filename makes downloads opt-in and avoids enumerable user URLs.
    if settings.get('publish_exports') and proto == 'vless':
        token = hashlib.sha256(record['client']['id'].encode()).hexdigest()
        web = Path('/home/vps/public_html/accounts')
        web.mkdir(parents=True, exist_ok=True)
        atomic(web / (token + '.txt'), content, 0o644)
        print(f'Download: https://{domain}/accounts/{token}.txt')
    print(content + f'Client JSON exports: {directory}')


def account(args):
    config, db, settings = load()
    users = db['accounts'].setdefault(args.protocol, {})
    action = args.action
    if action == 'list':
        for name, value in sorted(users.items()):
            if value.get('deleted'):
                continue
            print(name, value.get('expiry') or 'unmanaged expiry', ','.join(value['transports']))
        return
    user = valid_name(args.user or input('User: ').strip())
    if action == 'add':
        if user in users and not users[user].get('deleted'):
            raise ValueError('Account already exists')
        days = args.days if args.days is not None else int(input('Expiry in days: '))
        if days < 1:
            raise ValueError('Expiry must be positive')
        enabled = sorted({network(i) for i in config['inbounds'] if i.get('protocol') == args.protocol})
        if not enabled:
            raise ValueError(f'No {args.protocol} inbound configured')
        selected = [t.strip() for t in args.transports.split(',')] if args.transports else enabled
        if not set(selected) <= set(enabled):
            raise ValueError('Enable server transports first; enabled: ' + ','.join(enabled))
        credential = {'email': user}
        if args.protocol in ('vless', 'vmess'):
            credential['id'] = str(uuid.uuid4())
        else:
            credential['password'] = str(uuid.uuid4())
        if args.protocol == 'shadowsocks':
            credential['method'] = 'aes-128-gcm'
        if args.protocol == 'socks':
            credential = {'user': user, 'pass': str(uuid.uuid4())}
        users[user] = {'client': credential, 'expiry': (TODAY() + dt.timedelta(days=days)).isoformat(),
                       'transports': selected}
    elif user not in users:
        raise ValueError('Unknown account')
    elif action == 'renew':
        days = args.days if args.days is not None else int(input('Extend by days: '))
        if days < 1:
            raise ValueError('Days must be positive')
        base = max(TODAY(), dt.date.fromisoformat(users[user]['expiry'] or TODAY().isoformat()))
        users[user]['expiry'] = (base + dt.timedelta(days=days)).isoformat()
        users[user].pop('deleted', None)
    elif action == 'delete':
        # Tombstone retains identity so sync removes every copy, including additional transports.
        users[user]['expiry'] = '1970-01-01'
        users[user]['deleted'] = True
    if action == 'show' and (users[user].get('deleted') or
                            (users[user].get('expiry') and users[user]['expiry'] <= TODAY().isoformat())):
        raise ValueError('Account has expired or was deleted; renew it before exporting')
    if action != 'show':
        transaction(config, db, settings)
    if action == 'delete':
        shutil.rmtree(STATE / 'exports' / args.protocol / user, ignore_errors=True)
        token = hashlib.sha256(users[user]['client'].get('id', '').encode()).hexdigest()
        Path('/home/vps/public_html/accounts', token + '.txt').unlink(missing_ok=True)
        if args.protocol == 'vless':
            Path('/home/vps/public_html', 'vless-' + user + '.txt').unlink(missing_ok=True)
    else:
        exports(config, db, settings, args.protocol, user)


def expire(args):
    config, db, settings = load()
    transaction(config, db, settings)
    for proto, users in db['accounts'].items():
        for user, record in users.items():
            if record.get('expiry') and record['expiry'] <= TODAY().isoformat():
                shutil.rmtree(STATE / 'exports' / proto / valid_name(user), ignore_errors=True)
                token = hashlib.sha256(record['client'].get('id', '').encode()).hexdigest()
                Path('/home/vps/public_html/accounts', token + '.txt').unlink(missing_ok=True)
                if proto == 'vless':
                    Path('/home/vps/public_html', 'vless-' + user + '.txt').unlink(missing_ok=True)


def refresh(args):
    config, db, settings = load()
    for proto, users in db['accounts'].items():
        for name, record in users.items():
            if not record.get('deleted') and (not record.get('expiry') or record['expiry'] > TODAY().isoformat()):
                exports(config, db, settings, proto, name)


def activity(args):
    from collections import deque
    config, db, settings = load()
    logfile = config.get('log', {}).get('access')
    if not logfile or logfile == 'none' or not Path(logfile).is_file():
        print('No file-based Xray access log is configured; inspect the Xray service journal.')
        return
    users = db['accounts'].get(args.protocol, {})
    if args.user:
        if args.user not in users:
            raise ValueError('Unknown account')
        users = {args.user: users[args.user]}
    with open(logfile, errors='replace') as source:
        recent = deque(source, maxlen=1000)
    for line in recent:
        if any(re.search(r'(?<![A-Za-z0-9_.-])' + re.escape(user) + r'(?![A-Za-z0-9_.-])', line)
               for user in users):
            print(line.rstrip())


def enable(args):
    config, db, settings = load()
    if any(i.get('protocol') == 'vless' and network(i) == args.transport for i in config['inbounds']):
        print('Transport already enabled')
        return
    if args.transport == 'httpupgrade':
        args.httpupgrade, args.stage = True, False
        return migrate(args)
    port = free_port(config, args.port if args.port is not None else
                     (40000 if args.transport == 'kcp' else 8443), udp=args.transport == 'kcp')
    if args.address:
        import ipaddress
        try:
            address = str(ipaddress.ip_address(args.address))
        except ValueError:
            address = domain_name(args.address)
        settings.setdefault('direct_addresses', {})[args.transport] = address
    entry = inbound(args.transport, port)
    entry['listen'] = '0.0.0.0'
    if args.transport == 'raw':
        cert, key = settings['certificate'], settings['private_key']
        from stunnel import grant
        service_user = run('systemctl', 'show', settings.get('service', 'xray.service'),
                           '-p', 'User', '--value', capture=True).strip() or 'root'
        if service_user != 'root':
            grant(cert, service_user)
            grant(key, service_user)
        entry['streamSettings'].update(security='tls', tlsSettings={'minVersion': '1.2',
            'certificates': [{'certificateFile': cert, 'keyFile': key}]})
    else:
        entry['streamSettings']['kcpSettings'] = {'seed': str(uuid.uuid4())}
    config['inbounds'].append(entry)
    for record in db['accounts'].get('vless', {}).values():
        record['transports'].append(args.transport)
    transaction(config, db, settings)
    print(f'Allow {port}/{"udp" if args.transport == "kcp" else "tcp"} in your host and provider firewalls.')
    print('No global firewall policy changed. Export client configurations again.')


def fresh(args):
    if CONFIG.exists():
        raise ValueError('Existing Xray config found; use upgrade-existing.sh')
    config = {'log': {'loglevel': 'warning'}, 'inbounds': [],
              'outbounds': [{'tag': 'direct', 'protocol': 'freedom', 'settings': {}, 'mux': {'enabled': False}},
                            {'tag': 'blocked', 'protocol': 'blackhole', 'settings': {}}],
              'api': {'tag': 'api', 'services': ['StatsService']}, 'stats': {},
              'policy': {'levels': {'0': {'statsUserUplink': True, 'statsUserDownlink': True}},
                         'system': {'statsInboundUplink': True, 'statsInboundDownlink': True}},
              'routing': {'rules': [{'type': 'field', 'inboundTag': ['api'], 'outboundTag': 'api'},
                                   {'type': 'field', 'ip': ['10.0.0.0/8', '127.0.0.0/8', '169.254.0.0/16',
                                    '172.16.0.0/12', '192.168.0.0/16', '::1/128', 'fc00::/7', 'fe80::/10'],
                                    'outboundTag': 'blocked'}]}}
    config['inbounds'].append({'tag': 'api', 'listen': '127.0.0.1', 'port': free_port(config, 10085),
                               'protocol': 'dokodemo-door', 'settings': {'address': '127.0.0.1'}})
    routes, port = [], 11000
    for proto, ws, grpc in [('vless', '/vless', 'vless-grpc'), ('vmess', '/vmess', 'vmess-grpc'),
                             ('trojan', '/trojan-ws', 'trojan-grpc'), ('shadowsocks', '/ss-ws', 'ss-grpc')]:
        for net, endpoint in [('ws', ws), ('grpc', grpc)]:
            port += 1
            free_port(config, port)
            config['inbounds'].append(inbound(net, port, endpoint, proto))
            routes.append(route(net, '/' + endpoint if net == 'grpc' else endpoint, port))
    for net, endpoint, number in [('xhttp', '/xhttp/', 10086), ('httpupgrade', '/httpupgrade', 10087)]:
        endpoint = os.environ.get('XHTTP_PATH', endpoint) if net == 'xhttp' else endpoint
        if not re.fullmatch(r'/[A-Za-z0-9_/-]+', endpoint) or endpoint == '/':
            raise ValueError('Invalid endpoint')
        if net == 'xhttp':
            endpoint = endpoint.rstrip('/') + '/'
            number = int(os.environ.get('XHTTP_PORT', number))
        config['inbounds'].append(inbound(net, free_port(config, number), endpoint))
        routes.append(f'    # BEGIN BLUEBLUE {net}\n' + route(net, endpoint, number) + f'    # END BLUEBLUE {net}\n')
    site = Path('/etc/nginx/conf.d/blueblue.conf')
    if site.exists():
        raise ValueError('Blueblue site already exists')
    # HTTP service comes up first. Add Domains -> Renew Certificate activates the same site on 443.
    text = '''server {
    listen 80;
    server_name _;
    root /home/vps/public_html;
    location ^~ /.well-known/acme-challenge/ { root /home/vps/public_html; }
    location ^~ /accounts/ {
        if ($scheme != https) { return 403; }
        autoindex off;
        try_files $uri =404;
    }
    location / {
        proxy_pass http://127.0.0.1:700;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 5m;
    }
''' + ''.join(routes) + '}\n'
    settings = {'domain': '', 'nginx': str(site), 'config': str(CONFIG), 'binary': '/usr/local/bin/xray',
                'service': 'xray.service', 'certificate': '/etc/xray/xray.crt', 'private_key': '/etc/xray/xray.key',
                'publish_exports': True, 'tls_port': 443, 'ws_http_port': 80, 'fresh_site': True}
    transaction(config, {'schema': 1, 'accounts': {}}, settings, {site: text}, restart=False)


def get_url(url):
    if not url.startswith('https://'):
        raise ValueError('HTTPS required')
    req = urllib.request.Request(url, headers={'User-Agent': 'blueblue/2026', 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(req, timeout=120) as response:
        return response.read()


def release(args):
    machine = os.uname().machine
    arch = {'x86_64': '64', 'aarch64': 'arm64-v8a', 'armv7l': 'arm32-v7a',
            'armv6l': 'arm32-v6', 'i686': '32', 'riscv64': 'riscv64', 'ppc64le': 'ppc64le',
            's390x': 's390x', 'loongarch64': 'loong64'}.get(machine)
    if not arch:
        raise ValueError('Unsupported architecture: ' + machine)
    api = 'https://api.github.com/repos/XTLS/Xray-core/releases'
    if os.environ.get('XRAY_PRERELEASE') == '1':
        releases = json.loads(get_url(api + '?per_page=30'))
        selected = next(r for r in releases if not r['draft'])
    else:
        selected = json.loads(get_url(api + '/latest'))
        if selected['draft'] or selected['prerelease']:
            raise ValueError('Stable release API returned an unstable release')
    name = f'Xray-linux-{arch}.zip'
    assets = {a['name']: a for a in selected['assets']}
    asset, checksum = assets[name], assets[name + '.dgst']
    prefix = 'https://github.com/XTLS/Xray-core/releases/download/' + selected['tag_name'] + '/'
    if not all(a['browser_download_url'].startswith(prefix) for a in (asset, checksum)):
        raise ValueError('Unexpected official release URL')
    payload = get_url(asset['browser_download_url'])
    digest = get_url(checksum['browser_download_url']).decode()
    # Xray publishes SHA2-256=<hex> (older versions also use SHA256(file)=<hex>).
    candidates = re.findall(r'(?:SHA2?-?256)[^\n=]*[=:]\s*([0-9a-fA-F]{64})', digest, re.I)
    if not candidates or hashlib.sha256(payload).hexdigest() not in [x.lower() for x in candidates]:
        raise ValueError('Official Xray SHA256 checksum mismatch or missing')
    if asset.get('digest') and asset['digest'] != 'sha256:' + hashlib.sha256(payload).hexdigest():
        raise ValueError('GitHub asset digest mismatch')
    import io
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        binary = archive.read('xray')
        if not binary.startswith(b'\x7fELF'):
            raise ValueError('Expected Linux ELF binary')
        destination = Path(args.destination)
        destination.mkdir(parents=True, exist_ok=True)
        atomic(destination / 'xray', binary, 0o755)
        for name in ('geoip.dat', 'geosite.dat'):
            if name in archive.namelist():
                atomic(destination / name, archive.read(name), 0o644)
    atomic(destination / 'release.json', encoded({'version': selected['tag_name'], 'asset': asset['name'],
                                                'sha256': hashlib.sha256(payload).hexdigest()}))
    print(selected['tag_name'])


def main():
    global CONFIG
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('migrate')
    p.add_argument('--httpupgrade', action='store_true')
    p.add_argument('--stage', action='store_true')
    sub.add_parser('fresh')
    sub.add_parser('expire')
    sub.add_parser('refresh')
    p = sub.add_parser('activity')
    p.add_argument('protocol', choices=['vless', 'vmess', 'trojan', 'shadowsocks', 'socks'])
    p.add_argument('user', nargs='?')
    p = sub.add_parser('account')
    p.add_argument('protocol', choices=['vless', 'vmess', 'trojan', 'shadowsocks', 'socks'])
    p.add_argument('action', choices=['add', 'renew', 'delete', 'show', 'list'])
    p.add_argument('user', nargs='?')
    p.add_argument('--days', type=int)
    p.add_argument('--transports')
    p = sub.add_parser('enable')
    p.add_argument('transport', choices=['raw', 'kcp', 'httpupgrade'])
    p.add_argument('--port', type=int)
    p.add_argument('--address', help='Direct origin DNS/IP; TLS SNI keeps the configured domain')
    p = sub.add_parser('release')
    p.add_argument('destination')
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('Root privileges required')
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (nullcontext(None) if os.environ.get('BLUEBLUE_INSTALL_LOCKED') == '1' else
          open('/run/lock/blueblue.lock', 'w')) as lock:
        if lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
        if not os.environ.get('XRAY_CONFIG') and SETTINGS.exists():
            CONFIG = Path(read_json(SETTINGS, {})['config'])
        globals()[args.command](args)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as exc:
        sys.exit('Blueblue: ' + str(exc))
