# Bug2Eval 0.1.0 release verification

Verified 2026-09-29 on Windows with the bundled Python runtime.

- Existing tests plus three real regressions: **7 passed**.
- All three regressions were observed failing before application changes.
- Public cases B2E-001, B2E-002, B2E-003: before exit 1 / after exit 0.
- Packed case replay and artifact integrity: all three pass.
- Fresh virtual environment, wheel installed without dependencies: CLI version
  and all three public cases pass from outside the source directory.
- Wheel and source distribution build; `twine check` passes for both.
- Source compilation and `git diff --check` pass.
- Demo records four successful CLI commands; GIF and MP4 are edited replays
  of those outputs, not a model solve or a timing benchmark.

GitHub Actions runs tests and supported public cases on Windows, Linux, and macOS
with Python 3.10 and 3.13. Consult the live Actions results for remote matrix status.
The Windows quoting case is skipped on unsupported platforms by the collection runner.

This three-case collection consists of related project bugs. It does not establish
an agent performance baseline or justify general model quality claims.
