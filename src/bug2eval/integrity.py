from __future__ import annotations

from .errors import CaseValidationError
from .models import EvalCase, artifact_path
from .util import sha256_file


def verify_integrity(case: EvalCase) -> list[str]:
    checked: list[str] = []
    for name, artifact in case.data["artifacts"].items():
        rel = artifact.get("path")
        expected = artifact.get("sha256")
        if not rel or not expected:
            raise CaseValidationError(f"artifact {name!r} missing path or sha256")
        path = artifact_path(case.root, rel)
        if not path.is_file():
            raise CaseValidationError(f"artifact missing: {rel}")
        if path.stat().st_size != artifact['bytes']:
            raise CaseValidationError(f"artifact size mismatch for {rel}")
        actual = sha256_file(path)
        if actual != expected:
            raise CaseValidationError(f"artifact checksum mismatch for {rel}: expected {expected}, got {actual}")
        checked.append(rel)
    return checked
