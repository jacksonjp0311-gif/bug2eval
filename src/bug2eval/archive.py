from __future__ import annotations

import shutil
import tarfile
import zipfile
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from .errors import CaseValidationError


def _is_within(base: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def safe_extract_tar(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as tf:
        for member in tf.getmembers():
            target = destination / member.name
            if not _is_within(destination, target):
                raise CaseValidationError(f"unsafe path in archive: {member.name}")
            if member.isdev() or member.isfifo():
                raise CaseValidationError(f"unsupported special file in archive: {member.name}")
        tf.extractall(destination, filter="data")


def create_directory_tar(source: Path, output: Path, max_bytes: int) -> None:
    source = source.resolve()
    if not source.is_dir():
        raise FileNotFoundError(f"directory does not exist: {source}")
    total = 0
    files: list[Path] = []
    for path in source.rglob("*"):
        if path.is_symlink():
            continue
        if path.is_file():
            rel_parts = path.relative_to(source).parts
            if ".git" in rel_parts or "__pycache__" in rel_parts or ".pytest_cache" in rel_parts:
                continue
            total += path.stat().st_size
            if total > max_bytes:
                raise ValueError(
                    f"capture exceeds max size ({max_bytes} bytes). Increase --max-mb or capture a smaller reproducer."
                )
            files.append(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, "w:gz") as tf:
        for path in sorted(files):
            tf.add(path, arcname=path.relative_to(source), recursive=False)


def safe_extract_zip(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "r") as zf:
        for info in zf.infolist():
            target = destination / info.filename
            if not _is_within(destination, target):
                raise CaseValidationError(f"unsafe path in packed case: {info.filename}")
        zf.extractall(destination)


def pack_case(case_dir: Path, output: Path) -> Path:
    case_dir = case_dir.resolve()
    if not (case_dir / "metadata.json").is_file():
        raise CaseValidationError(f"not a Bug2Eval case: {case_dir}")
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(case_dir.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(case_dir))
    return output


@contextmanager
def open_case(path: Path):
    path = path.resolve()
    if path.is_dir():
        yield path
        return
    if path.is_file() and path.suffix.lower() == ".b2e":
        with TemporaryDirectory(prefix="bug2eval-case-") as tmp:
            dst = Path(tmp)
            safe_extract_zip(path, dst)
            yield dst
        return
    raise CaseValidationError(f"expected case directory or .b2e file: {path}")


def unpack_case(archive: Path, output: Path, force: bool = False) -> Path:
    archive = archive.resolve()
    output = output.resolve()
    if output.exists():
        if not force:
            raise FileExistsError(f"output already exists: {output}")
        if output.is_dir():
            shutil.rmtree(output)
        else:
            output.unlink()
    safe_extract_zip(archive, output)
    return output
