# Bug2Eval Agent Guide

This file is for coding agents modifying or integrating Bug2Eval.

## Product invariant

A valid case MUST demonstrate the same verifier failing on the captured **before** workspace and passing on the captured **after** workspace.

```text
before_exit != 0
and
after_exit == 0
```

Do not weaken this invariant to make a case pass.

## Stable interface

- `metadata.json` is the canonical machine-readable case contract.
- `schema_version` is currently `1.0`.
- `verification.argv` is an argument array and must be executed without a shell.
- `artifacts.*.sha256` must match before extraction or execution.
- `.b2e` is a ZIP archive containing one case at its root.
- A verifier exit code of `0` means pass; any other exit code means fail.

## When solving a case

1. Start from `workspace_before.tar.gz`.
2. Read `prompt.md` / `BUG2EVAL_TASK.md`.
3. Make the smallest correct fix.
4. Do not edit, remove, bypass, or neutralize the verifier.
5. Run the exact verification argv.
6. Return the workspace with the real fix applied.

## When modifying Bug2Eval itself

- Keep zero runtime dependencies unless there is a compelling reason to change the product contract.
- Preserve Windows/macOS/Linux behavior.
- Never extract archives without traversal checks.
- Never switch stored verifier execution to `shell=True`.
- Add regression tests for behavior changes.
- Keep human output concise and provide JSON for automation.

## Core modules

- `capture.py`: creates cases from Git refs or directory snapshots.
- `archive.py`: safe packing/extraction.
- `models.py`: case contract loading.
- `integrity.py`: SHA-256 verification.
- `runner.py`: validate and run workflows.
- `cli.py`: stable command-line interface.

## Integration evidence boundaries

Validation rejects verifier timeouts: a stalled process is not a reproduced assertion failure. Integrators must additionally classify the original failure; a nonzero exit alone cannot distinguish a bug from missing dependencies or a bad command. Keep infrastructure failures and flaky cases in a candidate queue.

During replay, `{prompt_file}` and `BUG2EVAL_PROMPT_FILE` now refer to a copy inside the disposable workspace, not the reference case directory. This reduces accidental reference disclosure; it does not create an OS sandbox. A solver returning nonzero or timing out cannot receive a passing solve even if it left a passing patch. Keep scripted/reference repairs separate from agent solve measurements.

Protect the verifier, supporting helpers, and configuration with repeatable `--protect PATH` arguments. Set up the same pinned dependencies in both snapshots. New tests must be overlaid identically into both snapshots with provenance recorded. Keep scoring and bundles outside the solver's writable scope, isolate untrusted programs, and retain holdout cases before tuning prompts.
