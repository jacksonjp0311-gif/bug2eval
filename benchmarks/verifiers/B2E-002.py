"""Regression: default packing must preserve dotted case names."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from bug2eval.cli import main

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    for name in ("case.v1", "case.v2"):
        case = root / name
        case.mkdir()
        (case / "metadata.json").write_text("{}", encoding="utf-8")
        assert main(["pack", str(case)]) == 0
        assert (root / (name + ".b2e")).is_file(), "dotted case name was truncated"
    assert not (root / "case.b2e").exists(), "case outputs collide"
print("PASS: dotted case names create distinct archives")
