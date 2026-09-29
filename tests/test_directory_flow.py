import sys
from pathlib import Path

from bug2eval.archive import open_case, pack_case
from bug2eval.capture import capture_directories
from bug2eval.models import load_case
from bug2eval.runner import run_case, validate_case


def make_pair(tmp_path: Path):
    before = tmp_path / "before"
    after = tmp_path / "after"
    before.mkdir()
    after.mkdir()
    verify = "from calc import value\nraise SystemExit(0 if value() == 42 else 1)\n"
    (before / "calc.py").write_text("def value():\n    return 0\n", encoding="utf-8")
    (before / "verify.py").write_text(verify, encoding="utf-8")
    (after / "calc.py").write_text("def value():\n    return 42\n", encoding="utf-8")
    (after / "verify.py").write_text(verify, encoding="utf-8")
    return before, after


def test_directory_capture_validate_pack_and_run(tmp_path: Path):
    before, after = make_pair(tmp_path)
    case_dir = capture_directories(
        before_dir=before,
        after_dir=after,
        output=tmp_path / "CASE-1",
        case_id="CASE-1",
        title="value returns 42",
        verify_argv=[sys.executable, "verify.py"],
    )
    case = load_case(case_dir)
    assert validate_case(case)["valid"] is True

    archive = pack_case(case_dir, tmp_path / "CASE-1.b2e")
    with open_case(archive) as unpacked:
        packed_case = load_case(unpacked)
        assert validate_case(packed_case)["valid"] is True

    agent = tmp_path / "agent.py"
    agent.write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "ws = Path(sys.argv[1])\n"
        "(ws / 'calc.py').write_text('def value():\\n    return 42\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )
    result = run_case(case, agent_argv=[sys.executable, str(agent), "{workspace}"], save_result=False)
    assert result["started_from_captured_failure"] is True
    assert result["passed"] is True
