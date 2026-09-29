# Bug2Eval v0.1.0

**Turn real bugs into reusable agent evals.**

Initial release includes Git and directory snapshot capture, deterministic validation, portable `.b2e` files, generic agent invocation, JSON automation output, artifact checksums, safe archive handling, result receipts, a zero-runtime-dependency Python package, an agent skill file, schema documentation, examples, tests, and cross-platform CI configuration.

The shortest demo:

```bash
bug2eval capture --id BUG-001 --title "real bug" --before-ref HEAD~1 --after-ref HEAD --verify "pytest -q"
bug2eval validate .bug2eval/cases/BUG-001
bug2eval pack .bug2eval/cases/BUG-001
```

**The bug became a benchmark.**
