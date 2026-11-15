"""Regression tests for fail-closed aggregate reports."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PROJECT_ROOT / "scripts"


@pytest.mark.parametrize(
    ("script_name", "extra_args"),
    [
        ("summarize_acl_main_runs.py", ["--bootstrap-samples", "10"]),
        ("summarize_external_utility_runs.py", []),
        ("summarize_ih_challenge_runs.py", ["--bootstrap-samples", "10"]),
        ("summarize_systems_benchmark.py", ["--bootstrap-samples", "10"]),
    ],
)
def test_empty_run_set_writes_failure_audit_and_exits_nonzero(
    tmp_path: Path,
    script_name: str,
    extra_args: list[str],
) -> None:
    out_dir = tmp_path / script_name
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / script_name),
            "--results-root",
            str(tmp_path / "missing-results"),
            "--run-prefix",
            "definitely_missing",
            "--out-dir",
            str(out_dir),
            *extra_args,
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    audit = json.loads(
        (out_dir / "data_quality_audit.json").read_text(encoding="utf-8")
    )
    assert audit["status"] == "fail"
