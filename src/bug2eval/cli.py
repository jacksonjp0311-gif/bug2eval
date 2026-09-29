from __future__ import annotations

import argparse
import json
import sys
import tarfile
import zipfile
from uuid import uuid4
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .archive import open_case, pack_case, unpack_case
from .capture import capture_directories, capture_git
from .errors import Bug2EvalError, CaseValidationError
from .integrity import verify_integrity
from .models import load_case
from .runner import run_case, validate_case
from .util import MAX_CAPTURE_BYTES_DEFAULT, parse_command, render_argv, slug_case_id, write_json

EXIT_OK = 0
EXIT_EVAL_FAILED = 1
EXIT_INVALID = 2
EXIT_TOOL_ERROR = 3


def _print_json(data: object) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def _tags(value: str | None) -> list[str]:
    if not value:
        return []
    return [x.strip() for x in value.split(",") if x.strip()]


def cmd_init(args) -> int:
    root = Path(args.path).resolve() / ".bug2eval"
    (root / "cases").mkdir(parents=True, exist_ok=True)
    config = root / "config.json"
    if not config.exists():
        write_json(config, {"schema_version": "1.0", "cases_dir": "cases"})
    print(f"Initialized Bug2Eval at {root}")
    return EXIT_OK


def cmd_capture(args) -> int:
    verify = parse_command(args.verify)
    args.case_id = slug_case_id(args.case_id)
    max_bytes = int(args.max_mb * 1024 * 1024)
    output = Path(args.output) if args.output else Path(".bug2eval") / "cases" / args.case_id
    common = dict(
        output=output, case_id=args.case_id, title=args.title, verify_argv=verify,
        timeout_sec=args.timeout, prompt_file=Path(args.prompt_file) if args.prompt_file else None,
        prompt_text=args.prompt_text, tags=_tags(args.tags), max_bytes=max_bytes, force=args.force,
    )
    if args.before_dir or args.after_dir:
        if not (args.before_dir and args.after_dir):
            raise ValueError("directory mode requires both --before-dir and --after-dir")
        case_dir = capture_directories(before_dir=Path(args.before_dir), after_dir=Path(args.after_dir), **common)
    else:
        case_dir = capture_git(repo=Path(args.repo), before_ref=args.before_ref, after_ref=args.after_ref, **common)
    with open_case(case_dir) as root:
        case = load_case(root)
        validation = validate_case(case) if not args.skip_validate else None
    if args.json:
        _print_json({"case": str(case_dir), "validation": validation})
    else:
        print(f"Captured {args.case_id} -> {case_dir}")
        if validation:
            print(f"Validation: {'VALID' if validation['valid'] else 'INVALID'}")
            for reason in validation["reasons"]:
                print(f"  - {reason}")
    return EXIT_OK if not validation or validation["valid"] else EXIT_INVALID


def cmd_validate(args) -> int:
    with open_case(Path(args.case)) as root:
        case = load_case(root)
        result = validate_case(case)
    if args.json:
        _print_json(result)
    else:
        print(f"{case.case_id}: {'VALID' if result['valid'] else 'INVALID'}")
        print(f"  before: exit {result['before']['exit_code']} (expected non-zero)")
        print(f"  after:  exit {result['after']['exit_code']} (expected 0)")
        for reason in result["reasons"]:
            print(f"  - {reason}")
    return EXIT_OK if result["valid"] else EXIT_INVALID


def cmd_run(args) -> int:
    agent = parse_command(args.agent_cmd) if args.agent_cmd else None
    case_path = Path(args.case).resolve()
    packed_case = case_path.is_file() and case_path.suffix.lower() == ".b2e"
    with open_case(case_path) as root:
        case = load_case(root)
        result = run_case(
            case, agent_argv=agent, agent_timeout_sec=args.agent_timeout,
            keep_workspace=Path(args.keep_workspace) if args.keep_workspace else None,
            save_result=(not args.no_save and not packed_case),
        )
    if packed_case and not args.no_save:
        results_dir = Path.cwd() / ".bug2eval" / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        result_path = results_dir / f"{result['case_id']}-{stamp}-{uuid4().hex}.json"
        write_json(result_path, result)
        result["result_file"] = str(result_path.resolve())
    if args.json:
        _print_json(result)
    else:
        print(f"{result['case_id']}: {'PASS' if result['passed'] else 'FAIL'}")
        if result["agent"]:
            print(f"  agent exit:  {result['agent']['exit_code']}")
        print(f"  verify exit: {result['after_verify']['exit_code']}")
        if result.get("result_file"):
            print(f"  result: {result['result_file']}")
    return EXIT_OK if result["passed"] else EXIT_EVAL_FAILED


def cmd_inspect(args) -> int:
    with open_case(Path(args.case)) as root:
        case = load_case(root)
        checked = verify_integrity(case)
        data = dict(case.data)
        data["integrity"] = {"ok": True, "checked": checked}
    if args.json:
        _print_json(data)
    else:
        print(f"{case.case_id} — {case.title}")
        print(f"Source: {case.data['source']['kind']}")
        print(f"Verify: {render_argv(case.verify_argv)}")
        print(f"Artifacts: {len(checked)} checksums OK")
        changed = case.data["source"].get("changed_files") or []
        if changed:
            print("Changed files:")
            for path in changed:
                print(f"  - {path}")
    return EXIT_OK


def cmd_pack(args) -> int:
    case_dir = Path(args.case).resolve()
    out = pack_case(case_dir, Path(args.output) if args.output else case_dir.with_name(case_dir.name + ".b2e"))
    print(out)
    return EXIT_OK


def cmd_unpack(args) -> int:
    archive = Path(args.archive).resolve()
    out = unpack_case(archive, Path(args.output) if args.output else archive.with_suffix(""), force=args.force)
    print(out)
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bug2eval", description="Turn fixed bugs into portable, deterministic evals for coding agents.")
    parser.add_argument("--version", action="version", version=f"bug2eval {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="initialize .bug2eval/ in a project")
    p.add_argument("path", nargs="?", default=".")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("capture", help="capture a fixed bug as a reusable eval")
    p.add_argument("--id", dest="case_id", required=True, help="stable case id, e.g. BUG-018")
    p.add_argument("--title", required=True)
    p.add_argument("--verify", required=True, help='verification command, e.g. "python -m pytest -q"')
    p.add_argument("--repo", default=".", help="git repository for ref mode")
    p.add_argument("--before-ref", default="HEAD~1")
    p.add_argument("--after-ref", default="HEAD")
    p.add_argument("--before-dir")
    p.add_argument("--after-dir")
    p.add_argument("--prompt-file")
    p.add_argument("--prompt-text")
    p.add_argument("--tags", help="comma-separated tags")
    p.add_argument("--timeout", type=int, default=120)
    p.add_argument("--max-mb", type=int, default=MAX_CAPTURE_BYTES_DEFAULT // (1024 * 1024))
    p.add_argument("--output")
    p.add_argument("--skip-validate", action="store_true")
    p.add_argument("--force", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_capture)

    p = sub.add_parser("validate", help="prove before fails and reference after passes")
    p.add_argument("case")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("run", help="run a case against an agent command or current workspace state")
    p.add_argument("case")
    p.add_argument("--agent-cmd", help="agent command; placeholders: {workspace}, {task_file}, {prompt_file}")
    p.add_argument("--agent-timeout", type=int, default=900)
    p.add_argument("--keep-workspace")
    p.add_argument("--no-save", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("inspect", help="show human or JSON case metadata and integrity")
    p.add_argument("case")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_inspect)

    p = sub.add_parser("pack", help="pack a case directory into one .b2e file")
    p.add_argument("case")
    p.add_argument("--output")
    p.set_defaults(func=cmd_pack)

    p = sub.add_parser("unpack", help="unpack a .b2e file")
    p.add_argument("archive")
    p.add_argument("--output")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_unpack)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (Bug2EvalError, ValueError, OSError, tarfile.TarError, zipfile.BadZipFile) as exc:
        code = EXIT_INVALID if isinstance(exc, CaseValidationError) else EXIT_TOOL_ERROR
        if getattr(args, 'json', False):
            _print_json({'error': str(exc), 'exit_code': code})
        else:
            print(f"bug2eval: error: {exc}", file=sys.stderr)
        return code
    except KeyboardInterrupt:
        print("bug2eval: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
