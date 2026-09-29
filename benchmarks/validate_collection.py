"""Replay all supported public cases, exiting nonzero on any invalid case."""
import json
import os
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
platform = {'win32': 'windows', 'darwin': 'macos'}.get(sys.platform, 'linux')
os.environ['PATH'] = str(Path(sys.executable).parent) + os.pathsep + os.environ['PATH']
manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
failed = False
for case in manifest['cases']:
    if platform not in case['platforms']:
        print(f"SKIP {case['id']}: unsupported platform {platform}", flush=True)
        continue
    cp = subprocess.run([sys.executable, '-m', 'bug2eval', 'validate', str(root / case['archive'])])
    failed = failed or cp.returncode != 0
raise SystemExit(1 if failed else 0)
