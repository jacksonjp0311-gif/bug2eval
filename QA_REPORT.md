# Bug2Eval v0.1.0 — QA Receipt

Date: 2026-09-29

## Verified in this build environment

- Python source compiles with `compileall`.
- Test suite: **4/4 passed**.
- Directory-pair capture: PASS.
- Git-ref capture: PASS.
- Before-fails / after-passes discrimination: PASS.
- SHA-256 tamper rejection: PASS.
- `.b2e` pack and safe unpack/read: PASS.
- `.b2e` validation: PASS.
- Generic command-based simulated agent repair: PASS.
- Result receipt persistence for packed `.b2e` runs: PASS.
- Wheel build: PASS.
- Fresh virtual-environment wheel install: PASS.
- Installed CLI `bug2eval --version`: PASS (`0.1.0`).

## Local environment used

- Linux
- Python 3.13.5
- Git 2.47.3

The repository also includes a GitHub Actions matrix for Python 3.10 and 3.13 across Ubuntu, macOS, and Windows. That matrix is configuration included in the release; only the local environment above was executed during this packaging session.

## Product invariant verified

```text
verify(before) != 0
verify(after)  == 0
```

The example eval `examples/EXAMPLE-001.b2e` satisfies this invariant and can be used as a smoke test.
