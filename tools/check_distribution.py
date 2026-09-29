"""Install a built wheel in a clean environment and replay supported cases."""
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

repo = Path(__file__).resolve().parents[1]
wheel = Path(sys.argv[1]).resolve()
if not wheel.is_file() or wheel.suffix != '.whl':
    raise SystemExit('Pass the path to a built wheel.')
with tempfile.TemporaryDirectory(prefix='bug2eval-install-') as tmp:
    root = Path(tmp)
    venv.EnvBuilder(with_pip=True).create(root / 'venv')
    scripts = root / 'venv' / ('Scripts' if os.name == 'nt' else 'bin')
    python = scripts / ('python.exe' if os.name == 'nt' else 'python')
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    env['PATH'] = str(scripts) + os.pathsep + env['PATH']
    for command in [
        [str(python), '-m', 'pip', 'install', '--no-deps', str(wheel)],
        [str(python), '-m', 'bug2eval', '--version'],
        [str(python), str(repo / 'benchmarks' / 'validate_collection.py')],
    ]:
        subprocess.run(command, cwd=root, env=env, check=True)
