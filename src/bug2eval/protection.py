"""File-integrity guards for verifier code. This is not a process sandbox."""
from __future__ import annotations

from pathlib import Path, PurePosixPath

from .errors import CaseValidationError
from .models import EvalCase, artifact_path
from .util import sha256_file

_CACHES = {'__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache'}


def protected_paths(case: EvalCase, *workspaces: Path) -> list[str]:
    """Combine explicit declarations with direct command files and test assets."""
    paths = set(case.data['verification'].get('protected_paths', []))
    argv = case.verify_argv
    candidates = []
    for arg in argv:
        token = arg.split('::', 1)[0].replace('\\', '/')
        if token and not token.startswith('-'):
            candidates.append(token)
    if '-m' in argv:
        index = argv.index('-m') + 1
        if index < len(argv):
            module = argv[index].replace('.', '/')
            candidates.extend([module + '.py', module])
    # Pytest discovery and supporting configuration can change the test outcome.
    if any(Path(arg).name.lower() in {'pytest', 'pytest.exe', 'py.test', 'py.test.exe'} for arg in argv):
        candidates.extend(['tests', 'test', 'conftest.py', 'pytest.ini', 'pyproject.toml', 'setup.cfg', 'tox.ini'])
        for workspace in workspaces:
            for pattern in ('test_*.py', '*_test.py'):
                candidates.extend(p.name for p in workspace.glob(pattern))
    for token in candidates:
        # Absolute executables and command strings are not workspace paths.
        try:
            for workspace in workspaces:
                path = artifact_path(workspace, token)
                if path.exists():
                    paths.add(PurePosixPath(token).as_posix())
        except (CaseValidationError, OSError, ValueError):
            continue
    if not paths:
        raise CaseValidationError('cannot identify protected verifier files; capture with --protect PATH for the verifier and its helpers')
    return sorted(paths)


def _fingerprint_path(workspace: Path, rel: str) -> dict[str, str]:
    path = artifact_path(workspace, rel)
    # A symlink in any component can redirect what is executed. Reject even
    # internal links, so replacing a verifier with a link cannot evade the guard.
    cursor = workspace
    for part in PurePosixPath(rel).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise CaseValidationError(f'protected verifier path is a symlink: {rel}')
    if not path.exists():
        raise CaseValidationError(f'protected verifier path is missing: {rel}')
    entries = [path, *sorted(path.rglob('*'))] if path.is_dir() else [path]
    fingerprints = {}
    for entry in entries:
        name = entry.relative_to(workspace).as_posix()
        if entry.is_symlink():
            raise CaseValidationError(f'protected verifier path is a symlink: {name}')
        if path.is_dir() and any(part in _CACHES for part in entry.relative_to(path).parts):
            continue
        if entry.is_dir():
            fingerprints[name] = 'directory'
        elif entry.is_file():
            fingerprints[name] = 'file:' + sha256_file(entry)
        else:
            raise CaseValidationError(f'unsupported protected verifier path: {name}')
    return fingerprints


def fingerprint(workspace: Path, paths: list[str]) -> dict[str, str]:
    result = {}
    for rel in paths:
        result.update(_fingerprint_path(workspace, rel))
    return result


def changed_paths(workspace: Path, paths: list[str], baseline: dict[str, str]) -> list[str]:
    current = {}
    changed = set()
    for rel in paths:
        try:
            current.update(_fingerprint_path(workspace, rel))
        except (CaseValidationError, OSError, ValueError):
            changed.add(rel)
    changed.update(name for name in baseline.keys() | current.keys() if baseline.get(name) != current.get(name))
    return sorted(changed)
