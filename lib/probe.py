#!/usr/bin/env python3
"""Read the effective Xray unit; refuse alternate/confdir layouts rather than guess."""
import json
import os
from pathlib import Path
import re
import shlex
import subprocess

service = os.environ.get('XRAY_SERVICE', 'xray.service')
unit = subprocess.check_output(['systemctl', 'cat', service], text=True)
entries = re.findall(r'^ExecStart=(.*)$', unit, re.M)
command = shlex.split(next(line for line in reversed(entries) if line.strip()))
if any('confdir' in word for word in command):
    raise SystemExit('Multiple-file Xray confdir layouts require manual consolidation before upgrade')
binary = str(Path(os.environ.get('XRAY_BINARY', command[0])).resolve(strict=True))
if binary != str(Path(command[0]).resolve(strict=True)):
    raise SystemExit('XRAY_BINARY must agree with the effective service executable')
config = None
for pos, word in enumerate(command):
    if word in ('-config', '--config', '-c'):
        config = command[pos + 1]
    elif word.startswith(('-config=', '--config=')):
        config = word.split('=', 1)[1]
if os.environ.get('XRAY_CONFIG') and config and Path(os.environ['XRAY_CONFIG']).resolve() != Path(config).resolve():
    raise SystemExit('XRAY_CONFIG must agree with the effective service command')
config = os.environ.get('XRAY_CONFIG', config)
if not config or not config.startswith('/'):
    raise SystemExit('Cannot detect one absolute Xray configuration path')
config = str(Path(config).resolve(strict=True))
user = subprocess.check_output(['systemctl', 'show', service, '-p', 'User', '--value'], text=True).strip() or 'root'
environment = shlex.split(subprocess.check_output(['systemctl', 'show', service, '-p', 'Environment', '--value'], text=True))
asset = next((value.split('=', 1)[1] for value in environment if value.startswith('XRAY_LOCATION_ASSET=')), None)
if asset is None:
    asset = '/usr/local/share/xray' if Path('/usr/local/share/xray').is_dir() else str(Path(binary).parent)
print(json.dumps({'binary': binary, 'config': config, 'service': service, 'user': user, 'assets': asset}))
