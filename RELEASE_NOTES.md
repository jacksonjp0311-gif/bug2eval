# Bug2Eval v0.1.2

This polish release makes invalid cases fail clearly before an agent runs, prevents
capture from overwriting its source, preserves existing cases when unpacking fails,
and keeps repeated run receipts distinct. Artifact paths are confined to the case
folder, and both sizes and SHA-256 hashes are checked.

The README quick start runs an existing public case immediately. CI now checks all
six platform/Python combinations plus a built wheel installed in a fresh environment.
The `CI passed` check summarizes those results; see Actions for current status.

The three original benchmark cases and their verifiers are unchanged. PyPI upload
remains pending authentication; install from GitHub or the attached wheel.
