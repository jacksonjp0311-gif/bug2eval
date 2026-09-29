from __future__ import annotations

import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .archive import safe_extract_tar
from .errors import CaseValidationError
from .integrity import verify_integrity
from .models import EvalCase
from .protection import changed_paths, fingerprint, protected_paths
from .util import render_argv, run_command, utc_now, write_json


def _workspace(case: EvalCase, which: str, root: Path) -> Path:
    ws = root / "workspace"
    archive = case.before_archive if which == "before" else case.after_archive
    safe_extract_tar(archive, ws)
    return ws


def _verification(case: EvalCase, workspace: Path):
    return run_command(
        case.verify_argv,
        cwd=workspace,
        timeout=case.timeout_sec,
        env={"BUG2EVAL_CASE_ID": case.case_id, "BUG2EVAL_PHASE": "verify"},
    )


def validate_case(case: EvalCase) -> dict:
    verify_integrity(case)
    with tempfile.TemporaryDirectory(prefix="bug2eval-validation-") as tmp:
        before_ws = _workspace(case, "before", Path(tmp) / 'before')
        after_ws = _workspace(case, "after", Path(tmp) / 'after')
        protected = protected_paths(case, before_ws, after_ws)
        before_files = fingerprint(before_ws, protected)
        after_files = fingerprint(after_ws, protected)
        before = _verification(case, before_ws)
        after = _verification(case, after_ws)
        modified = changed_paths(before_ws, protected, before_files) + changed_paths(after_ws, protected, after_files)
    same_verifier = before_files == after_files and not modified
    valid = before.exit_code != 0 and after.exit_code == 0 and same_verifier
    reasons: list[str] = []
    if not same_verifier:
        reasons.append('protected verifier files differ between snapshots or were modified during verification')
    if before.exit_code == 0:
        reasons.append("before snapshot already passes; eval does not discriminate the regression")
    if after.exit_code != 0:
        reasons.append("after snapshot fails; reference fix is not verified")
    return {
        "case_id": case.case_id,
        "valid": valid,
        "before": before.to_dict(),
        "after": after.to_dict(),
        "reasons": reasons,
        "verifier_integrity": {"protected_paths": protected, "intact": bool(same_verifier)},
    }


def _make_task(case: EvalCase, workspace: Path, protected: list[str]) -> Path:
    prompt = case.prompt_file.read_text(encoding="utf-8").rstrip()
    verify = render_argv(case.verify_argv)
    task = workspace / "BUG2EVAL_TASK.md"
    task.write_text(
        f"""# Bug2Eval Task: {case.case_id}

## Objective

{prompt}

## Success contract

- Work only inside this workspace.
- Do not weaken, skip, delete, or bypass the verification.
- Protected verifier paths (must remain unchanged): {', '.join(protected)}.
- Make the smallest correct fix that addresses the underlying bug.
- Verification command: `{verify}`
- A successful run exits with code 0.

When you are done, leave the workspace in the fixed state.
""",
        encoding="utf-8",
    )
    return task


def _expand_agent_argv(argv: list[str], workspace: Path, task_file: Path, prompt_file: Path) -> list[str]:
    mapping = {"{workspace}": str(workspace), "{task_file}": str(task_file), "{prompt_file}": str(prompt_file)}
    expanded = []
    for arg in argv:
        for key, value in mapping.items():
            arg = arg.replace(key, value)
        expanded.append(arg)
    return expanded


def run_case(
    case: EvalCase, *, agent_argv: list[str] | None, agent_timeout_sec: int = 900,
    keep_workspace: Path | None = None, save_result: bool = True,
) -> dict:
    validation = validate_case(case)
    if not validation['valid']:
        raise CaseValidationError('; '.join(validation['reasons']))
    with tempfile.TemporaryDirectory(prefix=f"bug2eval-{case.case_id}-") as temp_name:
        temp_root = Path(temp_name)
        workspace = _workspace(case, "before", temp_root)
        protected = validation['verifier_integrity']['protected_paths']
        task_file = _make_task(case, workspace, protected)
        verifier_files = fingerprint(workspace, protected)
        before = _verification(case, workspace)
        if before.exit_code == 0:
            raise CaseValidationError("before snapshot already passes; cannot score an agent on a non-discriminating case")
        if changed_paths(workspace, protected, verifier_files):
            raise CaseValidationError('baseline verification modified protected verifier files')
        agent = None
        if agent_argv:
            expanded = _expand_agent_argv(agent_argv, workspace, task_file, case.prompt_file)
            agent = run_command(
                expanded,
                cwd=workspace,
                timeout=agent_timeout_sec,
                env={
                    "BUG2EVAL_CASE_ID": case.case_id,
                    "BUG2EVAL_WORKSPACE": str(workspace),
                    "BUG2EVAL_TASK_FILE": str(task_file),
                    "BUG2EVAL_PROMPT_FILE": str(case.prompt_file),
                    "BUG2EVAL_VERIFY_COMMAND": render_argv(case.verify_argv),
                },
            )
        tampered = changed_paths(workspace, protected, verifier_files)
        if tampered:
            after_result = {'argv': case.verify_argv, 'exit_code': None, 'stdout': '',
                            'stderr': 'protected verifier files changed; verification skipped',
                            'duration_seconds': 0, 'timed_out': False, 'skipped': True}
        else:
            after_result = _verification(case, workspace).to_dict()
            tampered = changed_paths(workspace, protected, verifier_files)
        result = {
            "schema_version": "1.0",
            "case_id": case.case_id,
            "title": case.title,
            "started_from_captured_failure": before.exit_code != 0,
            "passed": not tampered and after_result['exit_code'] == 0,
            "created_at": utc_now(),
            "before_verify": before.to_dict(),
            "agent": agent.to_dict() if agent else None,
            "after_verify": after_result,
            "verifier_integrity": {"protected_paths": protected, "intact": not tampered, "changed_paths": tampered},
        }
        if keep_workspace:
            keep_workspace = keep_workspace.resolve()
            if keep_workspace.exists():
                raise FileExistsError(f"keep-workspace destination already exists: {keep_workspace}")
            shutil.copytree(workspace, keep_workspace)
            result["workspace_saved_to"] = str(keep_workspace)
    if save_result:
        results_dir = case.root / "results"
        results_dir.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        result_path = results_dir / f"run-{stamp}.json"
        idx = 1
        while result_path.exists():
            result_path = results_dir / f"run-{stamp}-{idx}.json"
            idx += 1
        write_json(result_path, result)
        result["result_file"] = str(result_path)
    return result
