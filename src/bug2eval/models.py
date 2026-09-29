from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .errors import CaseValidationError
from .util import read_json, write_json

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


def load_case(case_dir: Path) -> EvalCase:
    metadata = case_dir / "metadata.json"
    if not metadata.is_file():
        raise CaseValidationError(f"missing metadata.json in {case_dir}")
    data = read_json(metadata)
    missing = REQUIRED_TOP - set(data)
    if missing:
        raise CaseValidationError(f"metadata missing fields: {', '.join(sorted(missing))}")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise CaseValidationError(f"unsupported schema_version={data.get('schema_version')!r}; expected {SCHEMA_VERSION!r}")
    if not isinstance(data.get("verification", {}).get("argv"), list):
        raise CaseValidationError("verification.argv must be an array")
    return EvalCase(case_dir, data)


def save_case(case_dir: Path, data: dict) -> EvalCase:
    write_json(case_dir / "metadata.json", data)
    return load_case(case_dir)
