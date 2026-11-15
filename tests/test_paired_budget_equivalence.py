from __future__ import annotations

import json
import pathlib
import subprocess
import sys

from scripts.audit_paired_budget_equivalence import (
    PairSpec,
    audit_pair,
    parse_pair_spec,
)


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_paired_budget_equivalence.py"


def write_rows(
    root: pathlib.Path,
    run: str,
    method: str,
    retained: int,
    protected_fraction: float | None,
) -> None:
    run_dir = root / run
    run_dir.mkdir(parents=True)
    rows = []
    for index in range(2):
        audit = []
        if protected_fraction is not None:
            audit = [
                {
                    "layer": 0,
                    "protected_kept_fraction": protected_fraction,
                }
            ]
        rows.append(
            {
                "example_id": f"e{index}",
                "method": method,
                "keep_ratio": 0.2,
                "status": "ok",
                "model": "model",
                "dataset": "dataset.jsonl",
                "example_index": index,
                "category": "conflict",
                "expected_behavior": {"decision": "FOLLOW_SYSTEM"},
                "prompt_tokens": 100,
                "retained_prompt_tokens": retained,
                "retained_prompt_tokens_min": retained,
                "retained_prompt_tokens_max": retained,
                "press_audit": audit,
            }
        )
    (run_dir / "predictions.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_parse_pair_spec() -> None:
    assert parse_pair_spec("x|base|b|comparison|c|2") == PairSpec(
        "x", "base", "b", "comparison", "c", 2
    )


def test_audit_pair_passes_only_for_exact_budget_match(
    tmp_path: pathlib.Path,
) -> None:
    write_rows(tmp_path, "base", "b", 20, None)
    write_rows(tmp_path, "comparison", "c", 20, 1.0)
    spec = PairSpec("x", "base", "b", "comparison", "c", 2)
    report = audit_pair(tmp_path, spec)
    assert report["status"] == "PASS"
    assert report["paired_rows"] == 2
    assert not any(report["budget_field_mismatches"].values())
    assert not any(report["identity_field_mismatches"].values())

    rows_path = tmp_path / "comparison" / "predictions.jsonl"
    rows = [json.loads(line) for line in rows_path.read_text().splitlines()]
    rows[0]["retained_prompt_tokens"] = 21
    rows_path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )
    failed = audit_pair(tmp_path, spec)
    assert failed["status"] == "FAIL"
    assert failed["budget_field_mismatches"]["retained_prompt_tokens"] == 1

    rows[0]["retained_prompt_tokens"] = 20
    rows[0]["model"] = "different-model"
    rows_path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )
    identity_failed = audit_pair(tmp_path, spec)
    assert identity_failed["status"] == "FAIL"
    assert identity_failed["identity_field_mismatches"]["model"] == 1


def test_protected_fraction_accepts_float32_roundoff_only(
    tmp_path: pathlib.Path,
) -> None:
    write_rows(tmp_path, "base", "b", 20, None)
    write_rows(tmp_path, "comparison", "c", 20, 0.99999994)
    spec = PairSpec("x", "base", "b", "comparison", "c", 2)
    report = audit_pair(tmp_path, spec)
    assert report["status"] == "PASS"
    assert report["protected_fraction_below_one"] == 0

    path = tmp_path / "comparison" / "predictions.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    for row in rows:
        row["press_audit"][0]["protected_kept_fraction"] = 0.999
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )
    failed = audit_pair(tmp_path, spec)
    assert failed["status"] == "FAIL"
    assert failed["protected_fraction_below_one"] == 2


def test_nonempty_error_field_is_not_an_ok_pair(
    tmp_path: pathlib.Path,
) -> None:
    write_rows(tmp_path, "base", "b", 20, None)
    write_rows(tmp_path, "comparison", "c", 20, 1.0)
    path = tmp_path / "comparison" / "predictions.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[0]["error"] = "hidden failure"
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )
    spec = PairSpec("x", "base", "b", "comparison", "c", 2)
    report = audit_pair(tmp_path, spec)
    assert report["status"] == "FAIL"
    assert report["non_ok_pairs"] == 1
    assert report["runtime_error_pairs"] == 1


def test_cli_is_fail_closed_on_incomplete_pair(
    tmp_path: pathlib.Path,
) -> None:
    out = tmp_path / "audit.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--results-root",
            str(tmp_path),
            "--pair",
            "x|missing_base|b|missing_comparison|c|2",
            "--out",
            str(out),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 1
    assert json.loads(out.read_text())["status"] == "FAIL"


def test_cli_rejects_duplicate_pair_specs(
    tmp_path: pathlib.Path,
) -> None:
    write_rows(tmp_path, "base", "b", 20, None)
    write_rows(tmp_path, "comparison", "c", 20, 1.0)
    out = tmp_path / "audit.json"
    spec = "x|base|b|comparison|c|2"
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--results-root",
            str(tmp_path),
            "--pair",
            spec,
            "--pair",
            spec,
            "--out",
            str(out),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    payload = json.loads(out.read_text())
    assert completed.returncode == 1
    assert payload["status"] == "FAIL"
    assert payload["duplicate_spec_names"] == ["x"]
    assert len(payload["duplicate_spec_identities"]) == 1
