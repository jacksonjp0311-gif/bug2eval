# Security

Bug2Eval evaluates code and therefore crosses a trust boundary.

- Inspect third-party `.b2e` files before executing them.
- Run untrusted cases inside an OS/container sandbox.
- Do not capture secrets, credentials, `.env` files, or production data.
- Verifiers are executed as direct argv lists (`shell=False`).
- Archive extraction rejects path traversal and special device files.
- Checksums protect case integrity, not publisher authenticity.

Verifier protection detects changes to declared/inferred files and directories,
including deletion, symlink replacement, and additions to a protected directory.
It checks before and after scoring and rejects modified verifier code before
running it. A protection failure cannot produce a passing run receipt.

This is not OS isolation. Agents and evaluated application code execute with the
calling user's permissions. They can access host files, launch child processes,
or interfere with the test runtime. File hashes do not prevent every adversarial
bypass (such as process termination or monkeypatching from application code).
For adversarial scoring, run agents and scoring in separately controlled sandboxes,
keep authoritative verifiers outside agent write access, and declare all verifier
dependencies with `--protect`. Public cases are not a substitute for that boundary.
