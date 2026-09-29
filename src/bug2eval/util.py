from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .errors import CommandExecutionError

MAX_CAPTURE_BYTES_DEFAULT = 100 * 1024 * 1024
MAX_RESULT_TEXT = 64 * 1024


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slug_case_id(value: str) -> str:
    cleaned = []
    for ch in value.strip():
        if ch.isalnum() or ch in "-_.":
            cleaned.append(ch)
        elif ch.isspace():
            cleaned.append("-")
    out = "".join(cleaned).strip("-_.")
    if not out:
        raise ValueError("case id must contain at least one letter or number")
    return out[:120]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_command(command: str) -> list[str]:
    if not command or not command.strip():
        raise ValueError("command cannot be empty")
    argv = shlex.split(command, posix=(os.name != "nt"))
    if not argv:
        raise ValueError("command cannot be empty")
    return argv


def render_argv(argv: Iterable[str]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(list(argv))
    return shlex.join(list(argv))


def truncate(text: str, limit: int = MAX_RESULT_TEXT) -> str:
    if len(text) <= limit:
        return text
    omitted = len(text) - limit
    return text[:limit] + f"\n... [truncated {omitted} chars]"


@dataclass
class CommandResult:
    argv: list[str]
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False

    def to_dict(self) -> dict:
        return {
            "argv": self.argv,
            "exit_code": self.exit_code,
            "stdout": truncate(self.stdout),
            "stderr": truncate(self.stderr),
            "duration_seconds": round(self.duration_seconds, 4),
            "timed_out": self.timed_out,
        }


def run_command(argv: list[str], *, cwd: Path, timeout: int, env: dict[str, str] | None = None) -> CommandResult:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    start = time.monotonic()
    try:
        cp = subprocess.run(
            argv,
            cwd=str(cwd),
            env=merged_env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        return CommandResult(argv, cp.returncode, cp.stdout, cp.stderr, time.monotonic() - start)
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return CommandResult(
            argv,
            124,
            stdout or "",
            (stderr or "") + f"\nBug2Eval: timed out after {timeout}s",
            time.monotonic() - start,
            True,
        )
    except OSError as exc:
        raise CommandExecutionError(f"could not execute {argv[0]!r}: {exc}") from exc
