# Bug2Eval public benchmark collection

Three real bugs discovered in Bug2Eval during its 2026-09-29 release review.
These are observed defects in the original desktop source, not injected mutations
or production incident claims. This is a small seed collection, not a representative
agent leaderboard. No model scores have been measured.

| Case | Observed defect | Platforms |
|---|---|---|
| B2E-001 | Packing into the case folder embeds the output archive in itself | Windows, Linux, macOS |
| B2E-002 | `case.v1` and `case.v2` both pack to `case.b2e` | Windows, Linux, macOS |
| B2E-003 | Windows command parsing retains/misreads quotes and breaks execution | Windows only |

Each case includes MIT-licensed source snapshots, a task, hashes, exact Git provenance,
and a validation receipt. All three were replayed locally on Windows: **before exit 1,
after exit 0**, with identical verifier bytes. CI replays supported cases on its matrix.
The Windows case intentionally errors on other platforms; it must not count as a pass.
Run with Python 3.10+ available as `python` on PATH.

```bash
python -m pip install -e .
python -m bug2eval validate benchmarks/B2E-001.b2e
python -m bug2eval inspect benchmarks/B2E-001.b2e --json
python benchmarks/validate_collection.py
```

The original source is commit `855c4a9`; `1652799` adds the failing verifiers without
changing application code; `ddec8ed` fixes the three bugs without changing verifiers.
The snapshots share those before/after commits, but each verifier targets one defect.
This shared provenance means the three cases are correlated.

## Add the next real bug

1. Preserve the broken code before editing it. Remove secrets and private data.
2. Write a deterministic verifier and run it against that code. Check that it fails
   for the actual bug, not a missing dependency or setup failure.
3. Commit the failing verifier, then fix only the application code and commit again.
4. Capture those refs with the same verifier, validate, and pack the case.
5. Record the public source URL, immutable commits, license, platform/dependencies,
   failure evidence, and validation receipt in `manifest.json` and the case card.
6. Run `python benchmarks/validate_collection.py` before contributing.

Do not submit toy examples as real incidents, unsupported redistribution, secrets,
or flaky/network-dependent tests. The example under `examples/` is educational and
is not part of this collection. Captured snapshots include the reference fix for
auditability; keep that reference outside an evaluated agent's accessible workspace.

## Windows commands

Windows parsing uses the native
[CommandLineToArgvW API](https://learn.microsoft.com/en-us/windows/win32/api/shellapi/nf-shellapi-commandlinetoargvw).
Use double quotes for paths and arguments containing spaces within the stored command.
