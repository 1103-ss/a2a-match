#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess, sys

result = subprocess.run(
    ['npx', 'clawhub', '--workdir', '.', 'publish', '.',
     '--version', '2.8.0',
     '--changelog', 'v2.8.0: WebSocket realtime relay'],
    cwd='C:/Users/Administrator/.qclaw/workspace/a2a-match',
    capture_output=True, text=True,
    timeout=120
)
print('EXIT:', result.returncode)
print('STDOUT:', result.stdout[:2000])
print('STDERR:', result.stderr[:1000])
