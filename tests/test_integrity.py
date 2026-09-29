import sys
from pathlib import Path
import pytest

from bug2eval.capture import capture_directories
from bug2eval.errors import CaseValidationError
from bug2eval.integrity import verify_integrity
from bug2eval.models import load_case


def test_checksum_tampering_is_rejected(tmp_path: Path):
    before = tmp_path / "before"
    after = tmp_path / "after"
    before.mkdir(); after.mkdir()
    for root, code in [(before, 1), (after, 0)]:
        (root / "verify.py").write_text(f"raise SystemExit({code})\n", encoding="utf-8")
    case_dir = capture_directories(
        before_dir=before,
        after_dir=after,
        output=tmp_path / "CASE",
        case_id="CASE",
        title="tamper test",
        verify_argv=[sys.executable, "verify.py"],
    )
    case = load_case(case_dir)
    case.prompt_file.write_text("tampered", encoding="utf-8")
    with pytest.raises(CaseValidationError):
        verify_integrity(case)
