from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path, PurePosixPath, PureWindowsPath

from .errors import CaseValidationError
from .util import read_json, slug_case_id, write_json

SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class EvalCase:
    root: Path
    data: dict

    @property
    def case_id(self) -> str:
        return str(self.data["case_id"])

    @property
    def title(self) -> str:
        return str(self.data["title"])

    @property
    def verify_argv(self) -> list[str]:
        return list(self.data["verification"]["argv"])

    @property
    def timeout_sec(self) -> int:
        return int(self.data["verification"].get("timeout_sec", 120))

    @property
    def before_archive(self) -> Path:
        return self.root / self.data["artifacts"]["before"]["path"]

    @property
    def after_archive(self) -> Path:
        return self.root / self.data["artifacts"]["after"]["path"]

    @property
    def prompt_file(self) -> Path:
        return self.root / self.data["artifacts"]["prompt"]["path"]


REQUIRED_TOP = {"schema_version", "case_id", "title", "created_at", "source", "verification", "expected", "artifacts"}


def artifact_path(root: Path, rel: str) -> Path:
    """Resolve a portable artifact path without allowing it outside the case."""
    if (not isinstance(rel, str) or not rel or '\\' in rel or ':' in rel
            or PurePosixPath(rel).is_absolute() or PureWindowsPath(rel).anchor
            or '..' in PurePosixPath(rel).parts or '\x00' in rel):
        raise CaseValidationError(f"unsafe artifact path: {rel!r}")
    path = root / rel
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise CaseValidationError(f"artifact escapes case directory: {rel!r}") from exc
    return path


def load_case(case_dir: Path) -> EvalCase:
    metadata = case_dir / "metadata.json"
    if not metadata.is_file():
        raise CaseValidationError(f"missing metadata.json in {case_dir}")
    try:
        data = read_json(metadata)
    except (ValueError, UnicodeError) as exc:
        raise CaseValidationError(f"invalid metadata.json: {exc}") from exc
    if not isinstance(data, dict):
        raise CaseValidationError("metadata must be an object")
    missing = REQUIRED_TOP - set(data)
    if missing:
        raise CaseValidationError(f"metadata missing fields: {', '.join(sorted(missing))}")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise CaseValidationError(f"unsupported schema_version={data.get('schema_version')!r}; expected {SCHEMA_VERSION!r}")
    for field in ("case_id", "title", "created_at"):
        if not isinstance(data[field], str) or not data[field].strip():
            raise CaseValidationError(f"{field} must be a nonempty string")
    try:
        safe_id = slug_case_id(data['case_id'])
    except ValueError as exc:
        raise CaseValidationError(str(exc)) from exc
    if safe_id != data['case_id']:
        raise CaseValidationError("case_id must be a safe filename of at most 120 characters")
    source = data['source']
    if not isinstance(source, dict) or not isinstance(source.get('kind'), str) or not source['kind']:
        raise CaseValidationError("source.kind must be a nonempty string")
    if 'changed_files' in source and (not isinstance(source['changed_files'], list)
                                      or not all(isinstance(p, str) for p in source['changed_files'])):
        raise CaseValidationError("source.changed_files must be an array of strings")
    verification = data['verification']
    if not isinstance(verification, dict):
        raise CaseValidationError("verification must be an object")
    argv = verification.get('argv')
    if (not isinstance(argv, list) or not argv or not all(isinstance(arg, str) and '\x00' not in arg for arg in argv)
            or not argv[0].strip()):
        raise CaseValidationError("verification.argv must contain a nonempty executable and string arguments")
    timeout = verification.get('timeout_sec')
    if type(timeout) is not int or timeout < 1:
        raise CaseValidationError("verification.timeout_sec must be a positive integer")
    if 'protected_paths' in verification:
        paths = verification['protected_paths']
        if not isinstance(paths, list) or not paths:
            raise CaseValidationError('verification.protected_paths must be a nonempty array of relative paths')
        for rel in paths:
            artifact_path(case_dir, rel)
    expected = data['expected']
    if (not isinstance(expected, dict) or expected.get('before') != 'fail'
            or expected.get('after') != 'pass' or type(expected.get('verify_exit_code')) is not int
            or expected['verify_exit_code'] != 0):
        raise CaseValidationError("expected must require before=fail, after=pass, verify_exit_code=0")
    artifacts = data['artifacts']
    if not isinstance(artifacts, dict) or not {'before', 'after', 'prompt'} <= set(artifacts):
        raise CaseValidationError("artifacts must contain before, after and prompt")
    for name, artifact in artifacts.items():
        if not isinstance(artifact, dict):
            raise CaseValidationError(f"artifact {name!r} must be an object")
        artifact_path(case_dir, artifact.get('path'))
        digest = artifact.get('sha256')
        if not isinstance(digest, str) or not re.fullmatch('[a-f0-9]{64}', digest):
            raise CaseValidationError(f"artifact {name!r} must have a SHA-256 checksum")
        size = artifact.get('bytes')
        if type(size) is not int or size < 0:
            raise CaseValidationError(f"artifact {name!r} bytes must be a nonnegative integer")
    return EvalCase(case_dir, data)


def save_case(case_dir: Path, data: dict) -> EvalCase:
    write_json(case_dir / "metadata.json", data)
    return load_case(case_dir)
