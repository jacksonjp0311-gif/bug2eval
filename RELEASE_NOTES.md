# Bug2Eval v0.1.3

This patch fixes two reproduced problems: an agent could replace `verify.py` with
`pass` and receive a passing score, and `pack --output` could overwrite case metadata.

Runs now fingerprint protected verifier files and directories, reject changed or
missing paths, and skip scoring when the verifier was tampered with. The protected
content must match in both captured snapshots. Direct scripts and pytest assets
are inferred; declare custom helpers and fixtures with repeatable `--protect PATH`.
If no verifier files can be identified, validation fails with guidance to declare them.

Packing requires a `.b2e` output, protects case metadata/artifacts, rejects symlinks,
and replaces an existing bundle only after a complete temporary write. Failed writes
or replacement attempts preserve the previous bundle.

These are file-integrity checks, not an OS sandbox or a guarantee against every
adversarial scoring bypass. Use separate controlled agent/scoring environments for
untrusted code. The three original benchmark cases remain unchanged.

Install from GitHub or the attached wheel. PyPI remains unpublished.
