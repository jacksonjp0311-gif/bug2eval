# Contributing

1. Create a virtual environment.
2. `python -m pip install -e ".[dev]"`
3. Add or update tests.
4. Run `python -m pytest` and `python benchmarks/validate_collection.py`.
5. Keep the case-format invariants intact.

Small focused pull requests are preferred. New runtime dependencies require justification because zero-dependency installation is a product feature.

CI checks the test suite and supported benchmark cases on three operating systems
with Python 3.10 and 3.13. It also builds both distributions, checks their metadata,
and installs the wheel in a fresh environment. The `CI passed` check requires all
of those jobs to succeed. Historical failed commits retain their original status.
