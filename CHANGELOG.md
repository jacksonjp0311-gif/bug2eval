# 0.1.1

- Fix extraction on Python 3.10 builds without tarfile filters. Reject links and special files in the compatibility path; preserve traversal checks.
- Add five compatibility and archive safety regression checks.

# Changelog

## 0.1.0 — 2026-09-29

- Initial portable Bug2Eval case format.
- Git-ref and directory-pair capture.
- Deterministic before-fails / after-passes validation.
- Generic command-based agent runner.
- JSON/human CLI output.
- SHA-256 artifact integrity.
- `.b2e` pack/unpack support.
- Cross-platform CI workflow.
- Agent skill and integration documentation.
# Release review fixes

- Exclude a packed archive from its own input files.
- Preserve dotted case names in default `.b2e` output paths.
- Parse Windows command quoting with the native argument parser.
- Publish three verified real-bug cases and a recorded CLI launch demo.
