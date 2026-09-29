# Changelog

## 0.1.3 — 2026-09-29

- Fingerprint verifier files before agent execution; fail runs that modify, delete, or replace protected paths. Skip tampered verifiers.
- Require identical protected verifier content in both reference snapshots.
- Infer direct scripts and pytest assets; add repeatable `capture --protect PATH` for helpers and custom verification.
- Reject packing onto case metadata or artifacts, require a `.b2e` output, and replace bundles only after a successful temporary write.
- Document that verifier file integrity is not an adversarial process sandbox.

## 0.1.2 — 2026-09-29

- Validate case metadata, artifact paths, checksums, byte sizes, and verifier arguments before execution.
- Reject non-discriminating cases and invalid reference fixes before running an agent.
- Guard capture source directories and preserve existing cases when unpack input is corrupt.
- Return documented error codes and JSON errors; preserve timeout diagnostics and distinct run receipts.
- Add a working quick start, current-main CI badge, and fresh-wheel packaging checks.
- Modernize package license metadata and GitHub Actions; expose one aggregate `CI passed` check.

## 0.1.1 — 2026-09-29

- Support older Python 3.10 builds without tarfile extraction filters.
- Reject links and special files in the compatibility path while preserving traversal checks.
- Add five compatibility and archive safety regression checks.

## 0.1.0 — 2026-09-29

- Introduce Git/directory capture, portable `.b2e` cases, validation, generic agent execution, and JSON output.
- Add SHA-256 integrity checks, archive guards, documentation, examples, and cross-platform CI.
- Fix self-including archives, dotted output names, and Windows command quoting.
- Publish the first three real-bug benchmark cases and a recorded CLI demo.
