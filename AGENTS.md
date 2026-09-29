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
