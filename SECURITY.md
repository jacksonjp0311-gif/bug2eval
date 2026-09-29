# Security

Bug2Eval evaluates code and therefore crosses a trust boundary.

- Inspect third-party `.b2e` files before executing them.
- Run untrusted cases inside an OS/container sandbox.
- Do not capture secrets, credentials, `.env` files, or production data.
- Verifiers are executed as direct argv lists (`shell=False`).
- Archive extraction rejects path traversal and special device files.
- Checksums protect case integrity, not publisher authenticity.
