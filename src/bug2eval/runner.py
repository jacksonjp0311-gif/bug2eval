from __future__ import annotations

import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .archive import safe_extract_tar
from .errors import CaseValidationError
from .integrity import verify_integrity
from .models import EvalCase
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
    with tempfile.TemporaryDirectory(prefix="bug2eval-before-") as tmp:
        before_ws = _workspace(case, "before", Path(tmp))
        before = _verification(case, before_ws)
    with tempfile.TemporaryDirectory(prefix="bug2eval-after-") as tmp:
        after_ws = _workspace(case, "after", Path(tmp))
        after = _verification(case, after_ws)
    valid = before.exit_code != 0 and after.exit_code == 0
    reasons: list[str] = []
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
    }


def _make_task(case: EvalCase, workspace: Path) -> Path:
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
        task_file = _make_task(case, workspace)
        before = _verification(case, workspace)
        if before.exit_code == 0:
            raise CaseValidationError("before snapshot already passes; cannot score an agent on a non-discriminating case")
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
        after = _verification(case, workspace)
        result = {
            "schema_version": "1.0",
            "case_id": case.case_id,
            "title": case.title,
            "started_from_captured_failure": before.exit_code != 0,
            "passed": after.exit_code == 0,
            "created_at": utc_now(),
            "before_verify": before.to_dict(),
            "agent": agent.to_dict() if agent else None,
            "after_verify": after.to_dict(),
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
