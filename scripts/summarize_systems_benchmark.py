#!/usr/bin/env python3
"""Audit and summarize randomized repeated KVPress systems measurements."""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any

from summarize_acl_main_runs import (
    is_exact_decision_json,
    official_base_for,
    quantile,
)


FIELDS = [
    "prefill_seconds",
    "decode_seconds",
    "elapsed_seconds",
    "decode_tokens_per_second",
    "peak_memory_mb",
    "peak_incremental_memory_mb",
    "retained_prompt_tokens",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", default="results/authoritykv")
    parser.add_argument("--run-prefix", required=True)
    parser.add_argument("--out-dir", default="reports/randomized_systems")
    parser.add_argument("--bootstrap-samples", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20260530)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def read_exit_code(path: Path) -> int | None:
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def distribution(values: list[float]) -> dict[str, float | None]:
    return {
        "median": median(values) if values else None,
        "q1": quantile(values, 0.25),
        "q3": quantile(values, 0.75),
    }


def paired_bootstrap_median_delta(
    deltas: list[float],
    samples: int,
    rng: random.Random,
) -> tuple[float | None, float | None]:
    if not deltas or samples <= 0:
        return None, None
    draws: list[float] = []
    for _ in range(samples):
        sample = [deltas[rng.randrange(len(deltas))] for _ in deltas]
        draws.append(median(sample))
    return quantile(draws, 0.025), quantile(draws, 0.975)


def eligible(record: dict[str, Any]) -> bool:
    return record.get("status") == "ok" and record.get("error") is None


def per_example_median_deltas(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
    field: str,
) -> list[float]:
    """Aggregate repeated paired measurements to the registered prompt unit."""

    grouped: dict[str, list[float]] = defaultdict(list)
    for baseline, comparison in pairs:
        if (
            baseline.get(field) is None
            or comparison.get(field) is None
        ):
            continue
        example_id = str(comparison["example_id"])
        if str(baseline["example_id"]) != example_id:
            raise ValueError("paired systems rows have different examples")
        grouped[example_id].append(
            float(comparison[field]) - float(baseline[field])
        )
    return [
        median(grouped[example_id])
        for example_id in sorted(grouped)
    ]


def main() -> None:
    args = parse_args()
    root = Path(args.results_root)
    out_dir = Path(args.out_dir)
    run_dirs = sorted(
        path for path in root.glob(f"{args.run_prefix}*") if path.is_dir()
    )
    audit_runs: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    global_keys: set[tuple[str, int, str, float, str]] = set()
    global_duplicates: list[tuple[str, int, str, float, str]] = []

    for run_dir in run_dirs:
        config_path = run_dir / "run_config.json"
        predictions_path = run_dir / "judged_predictions.jsonl"
        metrics_path = run_dir / "metrics.json"
        exit_path = run_dir / "runner_exit_code.txt"
        missing = [
            str(path)
            for path in (
                config_path,
                predictions_path,
                metrics_path,
                exit_path,
            )
            if not path.exists()
        ]
        if missing:
            audit_runs.append(
                {"run_dir": str(run_dir), "status": "incomplete", "missing": missing}
            )
            continue
        config = load_json(config_path)
        rows = load_jsonl(predictions_path)
        methods = [str(method) for method in config.get("methods", [])]
        ratios = [float(ratio) for ratio in config.get("keep_ratios", [])]
        settings = sum(
            1 if method == "fullkv" else len(ratios) for method in methods
        )
        expected = (
            int(config.get("dataset_rows", 0))
            * int(config.get("repeats", 0))
            * settings
        )
        local_keys = [
            (
                int(row["repeat"]),
                str(row["method"]),
                float(row.get("keep_ratio", 1.0)),
                str(row["example_id"]),
            )
            for row in rows
        ]
        duplicate_num = len(local_keys) - len(set(local_keys))
        identity_mismatch = sum(
            str(row.get("run_id")) != str(config.get("run_id"))
            or str(row.get("model")) != str(config.get("model"))
            or str(row.get("dataset")) != str(config.get("dataset"))
            for row in rows
        )
        errors = sum(row.get("status") == "runtime_error" for row in rows)
        infeasible = sum(row.get("status") == "infeasible" for row in rows)
        runner_exit = read_exit_code(exit_path)
        status = "pass"
        if len(rows) != expected:
            status = "row_count_mismatch"
        if duplicate_num:
            status = "duplicate_keys"
        if identity_mismatch:
            status = "identity_mismatch"
        if errors:
            status = "runtime_errors"
        if runner_exit != 0:
            status = "nonzero_or_missing_exit_code"
        if not config.get("end_time"):
            status = "missing_end_time"
        audit_runs.append(
            {
                "run_dir": str(run_dir),
                "run_id": config.get("run_id"),
                "model": config.get("model"),
                "dataset": config.get("dataset"),
                "attn_implementation": config.get("attn_implementation"),
                "methods": methods,
                "keep_ratios": ratios,
                "repeats": config.get("repeats"),
                "expected_rows": expected,
                "observed_rows": len(rows),
                "duplicate_keys": duplicate_num,
                "identity_mismatch": identity_mismatch,
                "runtime_errors": errors,
                "infeasible": infeasible,
                "runner_exit_code": runner_exit,
                "experiment_config_sha256": config.get(
                    "experiment_config_sha256"
                ),
                "source_sha256": config.get("source_sha256"),
                "kvpress_commit": config.get("kvpress_commit"),
                "dataset_sha256": config.get("dataset_sha256"),
                "status": status,
            }
        )
        for row in rows:
            key = (
                str(config.get("run_id")),
                int(row["repeat"]),
                str(row["method"]),
                float(row.get("keep_ratio", 1.0)),
                str(row["example_id"]),
            )
            if key in global_keys:
                global_duplicates.append(key)
            global_keys.add(key)
            row["_systems_group"] = (
                "h2o_eager"
                if config.get("attn_implementation") == "eager"
                else "non_h2o"
            )
            records.append(row)

    grouped: dict[tuple[str, str, float], list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        grouped[
            (
                str(row["_systems_group"]),
                str(row["method"]),
                float(row.get("keep_ratio", 1.0)),
            )
        ].append(row)
    summary_rows: list[dict[str, Any]] = []
    for (systems_group, method, keep_ratio), rows in sorted(grouped.items()):
        usable = [row for row in rows if eligible(row)]
        repeat_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in usable:
            repeat_groups[str(row["example_id"])].append(row)
        repeat_agreement_den = sum(
            len(group) > 1 for group in repeat_groups.values()
        )
        repeat_agreement_num = sum(
            len(group) > 1
            and len(
                {
                    tuple(record.get("generated_token_ids", []))
                    for record in group
                }
            )
            == 1
            for group in repeat_groups.values()
        )
        summary: dict[str, Any] = {
            "systems_group": systems_group,
            "method": method,
            "keep_ratio": keep_ratio,
            "attempted_num": len(rows),
            "eligible_num": len(usable),
            "correct_num": sum(bool(row.get("correct")) for row in rows),
            "strict_schema_num": sum(
                is_exact_decision_json(row.get("output_text")) for row in rows
            ),
            "runtime_error_num": sum(
                row.get("status") == "runtime_error" for row in rows
            ),
            "infeasible_num": sum(
                row.get("status") == "infeasible" for row in rows
            ),
            "order_index_median": (
                median(float(row["order_index"]) for row in rows)
                if rows
                else None
            ),
            "repeat_token_agreement_num": repeat_agreement_num,
            "repeat_token_agreement_den": repeat_agreement_den,
            "repeat_token_agreement_rate": (
                repeat_agreement_num / repeat_agreement_den
                if repeat_agreement_den
                else None
            ),
        }
        for field in FIELDS:
            values = [
                float(row[field])
                for row in usable
                if row.get(field) is not None
            ]
            dist = distribution(values)
            summary[f"{field}_median"] = dist["median"]
            summary[f"{field}_q1"] = dist["q1"]
            summary[f"{field}_q3"] = dist["q3"]
        summary_rows.append(summary)

    lookup = {
        (
            str(row["_systems_group"]),
            int(row["repeat"]),
            str(row["example_id"]),
            str(row["method"]),
            float(row.get("keep_ratio", 1.0)),
        ): row
        for row in records
    }
    rng = random.Random(args.seed)
    comparison_rows: list[dict[str, Any]] = []
    for (systems_group, method, keep_ratio), rows in sorted(grouped.items()):
        if method == "fullkv":
            continue
        comparisons = [("compressed_vs_fullkv", "fullkv", 1.0)]
        base = official_base_for(method)
        if base is not None:
            comparisons.append(("authority_vs_official", base, keep_ratio))
        for comparison_type, baseline_method, baseline_ratio in comparisons:
            pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
            for row in rows:
                baseline = lookup.get(
                    (
                        systems_group,
                        int(row["repeat"]),
                        str(row["example_id"]),
                        baseline_method,
                        baseline_ratio,
                    )
                )
                if baseline is not None and eligible(row) and eligible(baseline):
                    pairs.append((baseline, row))
            if not pairs:
                continue
            result: dict[str, Any] = {
                "systems_group": systems_group,
                "comparison_type": comparison_type,
                "baseline": baseline_method,
                "comparison": method,
                "keep_ratio": keep_ratio,
                "paired_observation_num": len(pairs),
                "paired_example_num": len({
                    str(comparison["example_id"])
                    for _, comparison in pairs
                }),
                "paired_unit": "example",
            }
            for field in FIELDS:
                deltas = per_example_median_deltas(pairs, field)
                low, high = paired_bootstrap_median_delta(
                    deltas,
                    args.bootstrap_samples,
                    rng,
                )
                result[f"{field}_median_delta"] = (
                    median(deltas) if deltas else None
                )
                result[f"{field}_median_delta_ci95_low"] = low
                result[f"{field}_median_delta_ci95_high"] = high
                result[f"{field}_paired_example_num"] = len(deltas)
            comparison_rows.append(result)

    complete = [run for run in audit_runs if run.get("status") == "pass"]
    config_hashes = sorted(
        {
            str(run["experiment_config_sha256"])
            for run in complete
            if run.get("experiment_config_sha256")
        }
    )
    source_hashes = sorted(
        {
            str(run["source_sha256"])
            for run in complete
            if run.get("source_sha256")
        }
    )
    kvpress_commits = sorted(
        {
            str(run["kvpress_commit"])
            for run in complete
            if run.get("kvpress_commit")
        }
    )
    audit_status = "pass"
    if not run_dirs or global_duplicates:
        audit_status = "fail"
    if any(run.get("status") != "pass" for run in audit_runs):
        audit_status = "fail"
    if complete and (
        len(config_hashes) != 1
        or len(source_hashes) != 1
        or len(kvpress_commits) != 1
    ):
        audit_status = "fail"
    audit = {
        "status": audit_status,
        "run_prefix": args.run_prefix,
        "run_directories": len(run_dirs),
        "complete_runs": len(complete),
        "global_duplicate_keys": [list(key) for key in global_duplicates],
        "experiment_config_hashes": config_hashes,
        "source_hashes": source_hashes,
        "kvpress_commits": kvpress_commits,
        "runs": audit_runs,
    }
    write_json(out_dir / "data_quality_audit.json", audit)
    write_csv(out_dir / "systems_summary.csv", summary_rows)
    write_csv(out_dir / "paired_systems_comparisons.csv", comparison_rows)
    print(
        json.dumps(
            {
                "audit_status": audit_status,
                "run_directories": len(run_dirs),
                "summary_rows": len(summary_rows),
                "comparison_rows": len(comparison_rows),
                "out_dir": str(out_dir),
            },
            indent=2,
        )
    )
    if audit_status != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
