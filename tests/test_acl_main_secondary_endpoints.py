"""Integration coverage for paired ACL secondary endpoints."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUMMARIZER = ROOT / "scripts" / "summarize_acl_main_runs.py"


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def test_secondary_endpoints_are_paired_and_separately_corrected(
    tmp_path: Path,
) -> None:
    dataset = tmp_path / "dataset.jsonl"
    write_jsonl(dataset, [{"id": "conflict"}, {"id": "benign"}])
    run_dir = tmp_path / "results" / "registered_pair"
    run_dir.mkdir(parents=True)
    methods = [
        "kvpress_streaming",
        "authority_streaming_detected_provenance",
    ]
    rows: list[dict[str, object]] = []
    for method in methods:
        comparison = method.startswith("authority_")
        for index, (example_id, is_conflict) in enumerate(
            [("conflict", True), ("benign", False)]
        ):
            correct = comparison
            output = (
                '{"decision":"FOLLOW_SYSTEM"}'
                if comparison
                else "not valid JSON"
            )
            rows.append(
                {
                    "run_id": "registered_pair",
                    "example_index": index,
                    "example_id": example_id,
                    "category": "test",
                    "model": "test/model",
                    "dataset": str(dataset),
                    "method": method,
                    "keep_ratio": 0.2,
                    "status": "ok",
                    "error": None,
                    "is_conflict": is_conflict,
                    "is_benign": not is_conflict,
                    "correct": correct,
                    "authority_reversal": is_conflict and not comparison,
                    "malformed": not comparison,
                    "strict_json": comparison,
                    "output_text": output,
                    "press_audit": [],
                }
            )
    write_jsonl(run_dir / "predictions.jsonl", rows)
    write_jsonl(run_dir / "judged_predictions.jsonl", rows)
    write_json(
        run_dir / "run_config.json",
        {
            "run_id": "registered_pair",
            "end_time": "2026-07-25T00:00:00Z",
            "model": "test/model",
            "dataset": str(dataset),
            "dataset_sha256": "dataset",
            "methods": methods,
            "keep_ratios": [0.2],
            "limit": None,
            "experiment_config_sha256": "config",
            "source_sha256": "source",
            "kvpress_commit": "commit",
        },
    )
    write_json(
        run_dir / "metrics.json",
        {
            "fullkv_correct_conflict_ids": ["conflict"],
            "fullkv_correct_benign_ids": ["benign"],
        },
    )
    (run_dir / "runner_exit_code.txt").write_text("0\n", encoding="utf-8")
    (run_dir / "judge_exit_code.txt").write_text("0\n", encoding="utf-8")

    out_dir = tmp_path / "report"
    completed = subprocess.run(
        [
            sys.executable,
            str(SUMMARIZER),
            "--results-root",
            str(tmp_path / "results"),
            "--run-prefix",
            "registered_pair",
            "--out-dir",
            str(out_dir),
            "--bootstrap-samples",
            "100",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr

    with (out_dir / "paired_endpoint_comparisons.csv").open(
        encoding="utf-8",
        newline="",
    ) as handle:
        endpoint_rows = list(csv.DictReader(handle))
    assert {row["endpoint"] for row in endpoint_rows} == {
        "hierarchy_success",
        "benign_utility",
        "strict_json",
    }
    assert all(float(row["absolute_rate_delta"]) == 1.0 for row in endpoint_rows)
    assert all(
        "holm_adjusted_p_secondary_family" in row
        for row in endpoint_rows
    )

    with (out_dir / "paired_comparisons.csv").open(
        encoding="utf-8",
        newline="",
    ) as handle:
        primary_rows = list(csv.DictReader(handle))
    assert len(primary_rows) == 1
    assert float(primary_rows[0]["absolute_rate_delta"]) == -1.0
    assert "holm_adjusted_p_global_family" in primary_rows[0]
