# Bug2Eval Case Format v1.0

`metadata.json` is the canonical contract. A case contains a problem prompt, a broken workspace archive, a fixed reference archive, and an executable verifier contract.

## Required semantics

- `schema_version`: exact format version.
- `case_id`: stable human/machine identifier.
- `source`: provenance only; replay must not require the original repo.
- `verification.argv`: process argument array, executed directly without a shell.
- `expected.before`: `fail`.
- `expected.after`: `pass`.
- `artifacts`: path, SHA-256, and byte size.

## Portability

Paths inside metadata are relative to the case root. Workspace archives are `tar.gz`. A packed `.b2e` is a standard ZIP archive whose root is the case root.

Artifact paths use forward slashes. Absolute paths, parent traversal, and symlinks
that resolve outside the case are rejected. Hashes and recorded byte sizes must
both match. Case IDs must be safe filenames of at most 120 characters.

Verification requires a nonempty executable, string arguments, and a positive
integer timeout. The expected contract is always before=`fail`, after=`pass`, and
success exit code `0`. `run` validates both reference snapshots before invoking an
agent. It cannot award a pass for an already passing starting snapshot.

Malformed metadata and invalid case contracts return CLI exit code `2`. With
`--json`, errors are emitted as `{"error": "message", "exit_code": 2}`. Input and
system errors return `3`.

## Verifier protection

`verification.protected_paths` is an optional nonempty array of workspace-relative
file or directory paths. Capture it with repeatable `--protect PATH` options.
Declarations extend the paths inferred from direct command files and pytest test
assets. Validation fails closed if no paths can be identified. Protected paths
must exist, remain inside the workspace, contain no symlinks, and have identical
content in both reference snapshots. Python/test cache directories are ignored.

Run receipts add `verifier_integrity` containing `intact`, `protected_paths`, and
`changed_paths`. If tampering is detected before scoring, `after_verify.skipped`
is `true`, its `exit_code` is `null`, and the run is a failure (CLI exit `1`).
If scoring itself modifies protected files, the run also fails regardless of its
exit code. These guards detect file changes; they do not sandbox evaluated code.

## Compatibility promise

Readers should reject unknown major schema versions rather than guessing. Additive fields may appear within the same major version and should be ignored by readers that do not understand them.
