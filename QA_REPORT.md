# Bug2Eval 0.1.2 verification

Local review: 2026-09-29, Windows, Python 3.12.14.

- 37 tests pass, including metadata/path rejection, invalid-case scoring, source
  protection, staged capture/unpack, receipt collisions, and timeout diagnostics.
- All three original public cases validate: before exit 1, after exit 0.
- Original benchmark archives and immutable verifier files are unchanged.
- Source compilation and whitespace checks pass.
- Wheel/source builds pass strict Twine validation; the wheel is checked in a clean
  environment with no dependencies and replays every supported benchmark case.

The CI matrix covers Windows, macOS, and Linux on Python 3.10 and 3.13. Packaging
is a separate job, and the `CI passed` job requires every test and package job to
succeed. See the current-main badge in the README for live status.

Historical failures on the 0.1.0 commit remain visible; those were corrected in
0.1.1. The three-case corpus is a seed collection of related project bugs, not a
representative leaderboard. No agent scores are claimed.
