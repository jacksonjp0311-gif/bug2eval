"""Regression: packing inside a case must not include the output archive."""
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from bug2eval.archive import pack_case

with tempfile.TemporaryDirectory() as tmp:
    case = Path(tmp)
    (case / "metadata.json").write_text("{}", encoding="utf-8")
    (case / "payload.txt").write_text("real payload", encoding="utf-8")
    output = case / "bundle.b2e"
    for _ in range(2):
        pack_case(case, output)
        with zipfile.ZipFile(output) as zf:
            assert set(zf.namelist()) == {"metadata.json", "payload.txt"}, zf.namelist()
            assert zf.read("payload.txt") == b"real payload"
print("PASS: internal output excluded, including repeated packing")
