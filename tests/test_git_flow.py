import subprocess
import sys
from pathlib import Path

from bug2eval.capture import capture_git
from bug2eval.models import load_case
from bug2eval.runner import validate_case


def git(repo: Path, *args: str):
    subprocess.run(["git", "-C", str(repo), *args], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def test_git_capture(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Bug2Eval Test")
    (repo / "calc.py").write_text("def value():\n    return 0\n", encoding="utf-8")
    (repo / "verify.py").write_text("from calc import value\nraise SystemExit(0 if value() == 42 else 1)\n", encoding="utf-8")
    git(repo, "add", "."); git(repo, "commit", "-m", "broken")
    before = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True, stdout=subprocess.PIPE, check=True).stdout.strip()
    (repo / "calc.py").write_text("def value():\n    return 42\n", encoding="utf-8")
    git(repo, "add", "."); git(repo, "commit", "-m", "fix")
    after = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True, stdout=subprocess.PIPE, check=True).stdout.strip()
    case_dir = capture_git(
        repo=repo,
        before_ref=before,
        after_ref=after,
        output=tmp_path / "GIT-1",
        case_id="GIT-1",
        title="git flow",
        verify_argv=[sys.executable, "verify.py"],
    )
    case = load_case(case_dir)
    assert "calc.py" in case.data["source"]["changed_files"]
    assert validate_case(case)["valid"] is True
