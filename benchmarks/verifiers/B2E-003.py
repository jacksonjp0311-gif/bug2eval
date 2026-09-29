"""Regression: Windows quoted commands must execute without literal quotes."""
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from bug2eval.util import parse_command, run_command

if os.name != "nt":
    raise RuntimeError("B2E-003 requires Windows; it must not silently pass elsewhere")
argv = [sys.executable, "-c", "import sys; assert sys.argv[1:] == ['hello world', '', 'a\\\"b']", "hello world", "", 'a"b']
parsed = parse_command(subprocess.list2cmdline(argv))
assert parsed == argv, repr(parsed)
result = run_command(parsed, cwd=Path.cwd(), timeout=10)
assert result.exit_code == 0, result.stderr
print("PASS: quoted arguments, empty strings and embedded quotes execute correctly")
