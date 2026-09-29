# Bug2Eval 0.1.3 verification

Local review: 2026-09-29, Windows, Python 3.12.14.

- 64 tests pass; one symlink-creation test is skipped because this Windows account
  lacks permission to create symlinks. POSIX CI covers that test.
- Reproduced verifier replacement with `pass`, deletion, directory replacement,
  and additions to a protected helper directory. Each now fails the run.
- Tampered verifier code is skipped rather than executed. Legitimate application
  fixes still pass, and command-line JSON receipts report protection failures.
- Differing before/after verifier contents are rejected. Missing declarations and
  unknown verifier commands fail closed; capture supports repeatable `--protect`.
- Packing cannot overwrite case metadata or declared artifacts, including artifacts
  with a `.b2e` extension. Simulated write/replace failures preserve the old bundle.
- Repeated internal packing excludes itself and staging files.
- All three immutable benchmark cases validate unchanged.

Release checks build the wheel/source distribution, validate metadata with strict
Twine checks, install the wheel without dependencies in a clean environment, and
replay the original public cases. The CI matrix covers Python 3.10/3.13 across
Windows, Linux, and macOS, plus package installation and the aggregate CI check.

Verifier protection is file-integrity checking, not an OS sandbox or a guarantee
against all adversarial runtime manipulation. See SECURITY.md for that boundary.
