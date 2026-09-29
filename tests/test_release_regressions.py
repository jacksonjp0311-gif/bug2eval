import os
import runpy
from pathlib import Path

import pytest

VERIFIERS = Path(__file__).resolve().parents[1] / "benchmarks" / "verifiers"

@pytest.mark.parametrize("case_id", ["B2E-001", "B2E-002", "B2E-003"])
def test_release_regression(case_id):
    if case_id == "B2E-003" and os.name != "nt":
        pytest.skip("Windows command-line parsing regression")
    runpy.run_path(str(VERIFIERS / (case_id + ".py")), run_name="__main__")
