# B2E-002: Dotted case names collide when packed

This directory is a portable **Bug2Eval** regression case.

## Contract

- **Before snapshot:** expected to fail the verification command.
- **After snapshot:** expected to pass it.
- **Verification:** `python benchmarks/verifiers/B2E-002.py`
- **Timeout:** 120 seconds

## Changed files

- `src/bug2eval/archive.py`
- `src/bug2eval/cli.py`
- `src/bug2eval/util.py`

## Use

```bash
bug2eval validate .
bug2eval run . --agent-cmd "YOUR_AGENT_COMMAND"
bug2eval pack .
```

The canonical machine-readable contract is `metadata.json`.
