from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .archive import create_directory_tar
from .errors import Bug2EvalError
from .models import SCHEMA_VERSION, save_case
from .util import MAX_CAPTURE_BYTES_DEFAULT, sha256_file, slug_case_id, utc_now


def _prompt_text(title: str, prompt_file: Path | None, prompt_text: str | None) -> str:
    if prompt_file and prompt_text:
        raise ValueError("use either --prompt-file or --prompt-text, not both")
    if prompt_file:
        return prompt_file.read_text(encoding="utf-8")
    if prompt_text:
        return prompt_text
    return (
        f"# {title}\n\n"
        "Reproduce the captured failure, identify the cause, implement the smallest correct fix, "
        "and make the verification command pass without weakening the test.\n"
    )


def _write_case_readme(case_dir: Path, data: dict) -> None:
    verify = " ".join(data["verification"]["argv"])
    changed = data["source"].get("changed_files", [])
    changed_md = "\n".join(f"- `{x}`" for x in changed) or "- Not recorded"
    text = f"""# {data['case_id']}: {data['title']}

This directory is a portable **Bug2Eval** regression case.

## Contract

- **Before snapshot:** expected to fail the verification command.
- **After snapshot:** expected to pass it.
- **Verification:** `{verify}`
- **Timeout:** {data['verification']['timeout_sec']} seconds

## Changed files

{changed_md}

## Use

```bash
bug2eval validate .
bug2eval run . --agent-cmd \"YOUR_AGENT_COMMAND\"
bug2eval pack .
```

The canonical machine-readable contract is `metadata.json`.
"""
    (case_dir / "README.md").write_text(text, encoding="utf-8")


def _artifact(path: Path, case_dir: Path) -> dict:
    return {
        "path": path.relative_to(case_dir).as_posix(),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def _prepare_case_dir(output: Path, force: bool) -> Path:
    output = output.resolve()
    if output.exists():
        if not force:
            raise FileExistsError(f"case already exists: {output}; use --force to replace it")
        if output.is_dir():
            shutil.rmtree(output)
        else:
            output.unlink()
    output.mkdir(parents=True, exist_ok=False)
    (output / "artifacts").mkdir()
    return output


def capture_directories(
    *, before_dir: Path, after_dir: Path, output: Path, case_id: str, title: str,
    verify_argv: list[str], timeout_sec: int = 120, prompt_file: Path | None = None,
    prompt_text: str | None = None, tags: list[str] | None = None,
    max_bytes: int = MAX_CAPTURE_BYTES_DEFAULT, force: bool = False,
) -> Path:
    case_id = slug_case_id(case_id)
    case_dir = _prepare_case_dir(output, force)
    before = case_dir / "artifacts" / "workspace_before.tar.gz"
    after = case_dir / "artifacts" / "workspace_after.tar.gz"
    prompt = case_dir / "prompt.md"
    create_directory_tar(before_dir, before, max_bytes=max_bytes)
    create_directory_tar(after_dir, after, max_bytes=max_bytes)
    prompt.write_text(_prompt_text(title, prompt_file, prompt_text).rstrip() + "\n", encoding="utf-8")
    data = {
        "schema_version": SCHEMA_VERSION,
        "case_id": case_id,
        "title": title,
        "created_at": utc_now(),
        "source": {
            "kind": "directory_pair",
            "before": str(before_dir.resolve()),
            "after": str(after_dir.resolve()),
            "changed_files": [],
        },
        "verification": {"argv": verify_argv, "timeout_sec": timeout_sec},
        "expected": {"before": "fail", "after": "pass", "verify_exit_code": 0},
        "tags": tags or [],
        "artifacts": {
            "before": _artifact(before, case_dir),
            "after": _artifact(after, case_dir),
            "prompt": _artifact(prompt, case_dir),
        },
    }
    save_case(case_dir, data)
    _write_case_readme(case_dir, data)
    return case_dir


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    cp = subprocess.run(["git", "-C", str(repo), *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if check and cp.returncode != 0:
        raise Bug2EvalError(f"git {' '.join(args)} failed: {cp.stderr.strip()}")
    return cp


def _git_archive(repo: Path, ref: str, output: Path, max_bytes: int) -> None:
    resolved = _git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}").stdout.strip()
    cp = subprocess.run(
        ["git", "-C", str(repo), "archive", "--format=tar.gz", "-o", str(output), resolved],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if cp.returncode != 0:
        raise Bug2EvalError(f"git archive failed: {cp.stderr.strip()}")
    if output.stat().st_size > max_bytes:
        output.unlink(missing_ok=True)
        raise ValueError(f"compressed snapshot exceeds max size ({max_bytes} bytes). Increase --max-mb or capture a smaller reproducer.")


def capture_git(
    *, repo: Path, before_ref: str, after_ref: str, output: Path, case_id: str,
    title: str, verify_argv: list[str], timeout_sec: int = 120,
    prompt_file: Path | None = None, prompt_text: str | None = None,
    tags: list[str] | None = None, max_bytes: int = MAX_CAPTURE_BYTES_DEFAULT,
    force: bool = False,
) -> Path:
    repo = repo.resolve()
    if _git(repo, "rev-parse", "--is-inside-work-tree", check=False).returncode != 0:
        raise Bug2EvalError(f"not a git repository: {repo}")
    before_sha = _git(repo, "rev-parse", "--verify", f"{before_ref}^{{commit}}").stdout.strip()
    after_sha = _git(repo, "rev-parse", "--verify", f"{after_ref}^{{commit}}").stdout.strip()
    changed_raw = _git(repo, "diff", "--name-status", before_sha, after_sha).stdout.splitlines()
    changed = []
    for line in changed_raw:
        parts = line.split("\t")
        if len(parts) >= 2:
            changed.append(parts[-1])
    remote = _git(repo, "remote", "get-url", "origin", check=False)
    case_id = slug_case_id(case_id)
    case_dir = _prepare_case_dir(output, force)
    before = case_dir / "artifacts" / "workspace_before.tar.gz"
    after = case_dir / "artifacts" / "workspace_after.tar.gz"
    prompt = case_dir / "prompt.md"
    _git_archive(repo, before_sha, before, max_bytes=max_bytes)
    _git_archive(repo, after_sha, after, max_bytes=max_bytes)
    prompt.write_text(_prompt_text(title, prompt_file, prompt_text).rstrip() + "\n", encoding="utf-8")
    data = {
        "schema_version": SCHEMA_VERSION,
        "case_id": case_id,
        "title": title,
        "created_at": utc_now(),
        "source": {
            "kind": "git",
            "repository": str(repo),
            "remote": remote.stdout.strip() if remote.returncode == 0 else None,
            "before_ref": before_ref,
            "before_commit": before_sha,
            "after_ref": after_ref,
            "after_commit": after_sha,
            "changed_files": changed,
        },
        "verification": {"argv": verify_argv, "timeout_sec": timeout_sec},
        "expected": {"before": "fail", "after": "pass", "verify_exit_code": 0},
        "tags": tags or [],
        "artifacts": {
            "before": _artifact(before, case_dir),
            "after": _artifact(after, case_dir),
            "prompt": _artifact(prompt, case_dir),
        },
    }
    save_case(case_dir, data)
    _write_case_readme(case_dir, data)
    return case_dir
