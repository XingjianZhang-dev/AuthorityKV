#!/usr/bin/env python3
"""Audit and aggregate official LongBench/RULER KVPress utility runs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any


BASE_PAIRS = {
    "authority_streaming_detected_provenance": "kvpress_streaming",
    "authority_knorm_detected_provenance": "kvpress_knorm",
    "authority_h2o_detected_provenance": "kvpress_h2o",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", default="results/authoritykv")
    parser.add_argument(
        "--run-prefix",
        default="aclmain_20260725v1_qwen7b_utility_",
    )
    parser.add_argument("--out-dir", default="reports/acl_external_utility")
    parser.add_argument("--bootstrap-samples", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=260725)
    parser.add_argument(
        "--allowed-source-sha256",
        action="append",
        default=[],
        help=(
            "Repeat for each preregistered scientific source stratum. "
            "When supplied, the observed set must match exactly."
        ),
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def read_exit_code(path: Path) -> int | None:
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


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


def quantile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    position = probability * (len(values) - 1)
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return values[lower]
    weight = position - lower
    return values[lower] * (1 - weight) + values[upper] * weight


def distribution(records: list[dict[str, Any]], field: str) -> dict[str, float | None]:
    values = [
        float(record[field])
        for record in records
        if record.get(field) is not None
    ]
    return {
        "median": median(values) if values else None,
        "q1": quantile(values, 0.25),
        "q3": quantile(values, 0.75),
    }


def utility_score(record: dict[str, Any]) -> tuple[str, float | None]:
    dataset = Path(str(record.get("dataset", ""))).name.lower()
    if "ruler" in dataset:
        value = record.get("correct")
        return (
            "utility_accuracy",
            float(bool(value)) if value is not None else None,
        )
    value = record.get("longbench_score")
    return (
        "longbench_score",
        float(value) if value is not None else None,
    )


def paired_bootstrap_mean_ci(
    deltas: list[float],
    *,
    samples: int,
    seed: int,
) -> tuple[float | None, float | None]:
    if not deltas or samples <= 0:
        return None, None
    rng = random.Random(seed)
    size = len(deltas)
    estimates = [
        sum(deltas[rng.randrange(size)] for _ in range(size)) / size
        for _ in range(samples)
    ]
    return quantile(estimates, 0.025), quantile(estimates, 0.975)


def source_hashes_are_valid(
    observed: list[str],
    allowed: list[str],
) -> bool:
    observed_unique = sorted(set(observed))
    allowed_unique = sorted(set(allowed))
    return (
        observed_unique == allowed_unique
        if allowed_unique
        else len(observed_unique) == 1
    )


def paired_utility_comparisons(
    records: list[dict[str, Any]],
    *,
    bootstrap_samples: int,
    seed: int,
) -> list[dict[str, Any]]:
    lookup = {
        (
            str(record["dataset"]),
            str(record["method"]),
            float(record.get("keep_ratio", 1.0)),
            str(record["example_id"]),
        ): record
        for record in records
    }
    groups: dict[
        tuple[str, str, float],
        list[dict[str, Any]],
    ] = defaultdict(list)
    for record in records:
        method = str(record.get("method"))
        if method not in BASE_PAIRS:
            continue
        groups[
            (
                str(record["dataset"]),
                method,
                float(record.get("keep_ratio", 1.0)),
            )
        ].append(record)

    rows: list[dict[str, Any]] = []
    for (dataset, comparison, ratio), group in sorted(groups.items()):
        fullkv_scores: list[float] = []
        comparison_scores: list[float] = []
        missing_or_unscored = 0
        runtime_errors = 0
        score_fields: set[str] = set()
        for comparison_record in sorted(
            group,
            key=lambda record: str(record["example_id"]),
        ):
            fullkv_record = lookup.get(
                (
                    dataset,
                    "fullkv",
                    1.0,
                    str(comparison_record["example_id"]),
                )
            )
            if fullkv_record is None:
                missing_or_unscored += 1
                continue
            fullkv_field, fullkv_score = utility_score(fullkv_record)
            comparison_field, comparison_score = utility_score(
                comparison_record
            )
            score_fields.update((fullkv_field, comparison_field))
            if fullkv_score is None or comparison_score is None:
                missing_or_unscored += 1
                continue
            runtime_errors += int(
                fullkv_record.get("error") is not None
                or comparison_record.get("error") is not None
            )
            fullkv_scores.append(fullkv_score)
            comparison_scores.append(comparison_score)

        deltas = [
            comparison_score - fullkv_score
            for fullkv_score, comparison_score in zip(
                fullkv_scores,
                comparison_scores,
                strict=True,
            )
        ]
        seed_material = (
            f"{seed}|{dataset}|{comparison}|{ratio:.8f}"
        ).encode("utf-8")
        pair_seed = int.from_bytes(
            hashlib.sha256(seed_material).digest()[:8],
            "big",
        )
        ci_low, ci_high = paired_bootstrap_mean_ci(
            deltas,
            samples=bootstrap_samples,
            seed=pair_seed,
        )
        rows.append(
            {
                "dataset": dataset,
                "official_base": BASE_PAIRS[comparison],
                "comparison": comparison,
                "keep_ratio": ratio,
                "score_field": (
                    next(iter(score_fields))
                    if len(score_fields) == 1
                    else "inconsistent"
                ),
                "paired_num": len(deltas),
                "missing_or_unscored_pair_num": (
                    missing_or_unscored
                ),
                "runtime_error_num": runtime_errors,
                "fullkv_score": (
                    sum(fullkv_scores) / len(fullkv_scores)
                    if fullkv_scores
                    else None
                ),
                "comparison_score": (
                    sum(comparison_scores) / len(comparison_scores)
                    if comparison_scores
                    else None
                ),
                "absolute_score_delta": (
                    sum(deltas) / len(deltas) if deltas else None
                ),
                "absolute_score_delta_ci95_low": ci_low,
                "absolute_score_delta_ci95_high": ci_high,
                "bootstrap_samples": bootstrap_samples,
                "bootstrap_seed": pair_seed,
            }
        )
    return rows


def main() -> None:
    args = parse_args()
    root = Path(args.results_root)
    out_dir = Path(args.out_dir)
    run_dirs = sorted(path for path in root.glob(f"{args.run_prefix}*") if path.is_dir())
    audit_runs: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []

    for run_dir in run_dirs:
        config_path = run_dir / "run_config.json"
        predictions_path = run_dir / "predictions.jsonl"
        metrics_path = run_dir / "metrics.json"
        exit_path = run_dir / "runner_exit_code.txt"
        missing = [
            str(path)
            for path in (config_path, predictions_path, metrics_path, exit_path)
            if not path.exists()
        ]
        if missing:
            audit_runs.append(
                {"run_dir": str(run_dir), "status": "incomplete", "missing": missing}
            )
            continue
        config = load_json(config_path)
        predictions = load_jsonl(predictions_path)
        methods = [str(method) for method in config.get("methods", [])]
        ratios = [float(ratio) for ratio in config.get("keep_ratios", [])]
        examples = len({str(record["example_id"]) for record in predictions})
        configured_examples = int(config.get("dataset_rows", 0))
        combinations = sum(1 if method == "fullkv" else len(ratios) for method in methods)
        expected_rows = configured_examples * combinations
        errors = sum(record.get("error") is not None for record in predictions)
        runner_exit = read_exit_code(exit_path)
        keys = [
            (
                str(record["method"]),
                float(record.get("keep_ratio", 1.0)),
                str(record["example_id"]),
            )
            for record in predictions
        ]
        duplicate_keys = len(keys) - len(set(keys))
        identity_mismatch = sum(
            str(record.get("run_id")) != str(config.get("run_id"))
            or str(record.get("model")) != str(config.get("model"))
            or str(record.get("dataset")) != str(config.get("dataset"))
            for record in predictions
        )
        status = "pass"
        if len(predictions) != expected_rows:
            status = "row_count_mismatch"
        if examples != configured_examples:
            status = "dataset_example_count_mismatch"
        if duplicate_keys:
            status = "duplicate_keys"
        if identity_mismatch:
            status = "record_identity_mismatch"
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
                "dataset": config.get("dataset"),
                "methods": methods,
                "examples": examples,
                "configured_examples": configured_examples,
                "expected_rows": expected_rows,
                "prediction_rows": len(predictions),
                "errors": errors,
                "duplicate_keys": duplicate_keys,
                "identity_mismatch": identity_mismatch,
                "runner_exit_code": runner_exit,
                "status": status,
                "source_sha256": config.get("source_sha256"),
                "experiment_config_sha256": config.get("experiment_config_sha256"),
                "kvpress_commit": config.get("kvpress_commit"),
                "dataset_sha256": config.get("dataset_sha256"),
            }
        )
        records.extend(predictions)

    groups: dict[tuple[str, str, float], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[
            (
                str(record["dataset"]),
                str(record["method"]),
                float(record.get("keep_ratio", 1.0)),
            )
        ].append(record)
    summary_rows: list[dict[str, Any]] = []
    for (dataset, method, keep_ratio), group in sorted(groups.items()):
        warmed = [
            record for record in group if int(record.get("example_index", 0)) != 0
        ] or group
        prefill = distribution(warmed, "prefill_seconds")
        elapsed = distribution(warmed, "elapsed_seconds")
        memory = distribution(warmed, "peak_memory_mb")
        longbench = [
            float(record["longbench_score"])
            for record in group
            if record.get("longbench_score") is not None
        ]
        summary_rows.append(
            {
                "dataset": dataset,
                "method": method,
                "keep_ratio": keep_ratio,
                "num_examples": len(group),
                "utility_correct_num": sum(bool(record.get("correct")) for record in group),
                "utility_accuracy": (
                    sum(bool(record.get("correct")) for record in group) / len(group)
                ),
                "longbench_score": (
                    sum(longbench) / len(longbench) if longbench else None
                ),
                "errors": sum(record.get("error") is not None for record in group),
                "prefill_seconds_median": prefill["median"],
                "prefill_seconds_q1": prefill["q1"],
                "prefill_seconds_q3": prefill["q3"],
                "elapsed_seconds_median": elapsed["median"],
                "elapsed_seconds_q1": elapsed["q1"],
                "elapsed_seconds_q3": elapsed["q3"],
                "peak_memory_mb_median": memory["median"],
                "peak_memory_mb_q1": memory["q1"],
                "peak_memory_mb_q3": memory["q3"],
            }
        )

    lookup = {
        (
            str(record["dataset"]),
            str(record["method"]),
            float(record.get("keep_ratio", 1.0)),
            str(record["example_id"]),
        ): record
        for record in records
    }
    equivalence_rows: list[dict[str, Any]] = []
    mismatches = 0
    for (dataset, method, ratio, example_id), comparison in sorted(lookup.items()):
        base_method = BASE_PAIRS.get(method)
        if base_method is None:
            continue
        base = lookup.get((dataset, base_method, ratio, example_id))
        if base is None:
            continue
        token_equal = base.get("generated_token_ids") == comparison.get(
            "generated_token_ids"
        )
        text_equal = base.get("output_text") == comparison.get("output_text")
        if not token_equal or not text_equal:
            mismatches += 1
        equivalence_rows.append(
            {
                "dataset": dataset,
                "keep_ratio": ratio,
                "official_base": base_method,
                "authority_composition": method,
                "example_id": example_id,
                "token_ids_equal": token_equal,
                "text_equal": text_equal,
            }
        )

    paired_utility_rows = paired_utility_comparisons(
        records,
        bootstrap_samples=args.bootstrap_samples,
        seed=args.seed,
    )
    paired_utility_integrity_failures = sum(
        int(row["missing_or_unscored_pair_num"])
        + int(row["runtime_error_num"])
        + int(row["score_field"] == "inconsistent")
        for row in paired_utility_rows
    )

    audit_status = "pass"
    if not run_dirs:
        audit_status = "fail"
    if (
        any(run["status"] != "pass" for run in audit_runs)
        or mismatches
        or paired_utility_integrity_failures
    ):
        audit_status = "fail"
    complete_runs = [run for run in audit_runs if run.get("status") == "pass"]
    config_hashes = sorted(
        {
            str(run["experiment_config_sha256"])
            for run in complete_runs
            if run.get("experiment_config_sha256")
        }
    )
    source_hashes = sorted(
        {
            str(run["source_sha256"])
            for run in complete_runs
            if run.get("source_sha256")
        }
    )
    kvpress_commits = sorted(
        {
            str(run["kvpress_commit"])
            for run in complete_runs
            if run.get("kvpress_commit")
        }
    )
    dataset_hashes: dict[str, set[str]] = defaultdict(set)
    for run in complete_runs:
        if run.get("dataset") and run.get("dataset_sha256"):
            dataset_hashes[str(run["dataset"])].add(str(run["dataset_sha256"]))
    inconsistent_dataset_hashes = {
        dataset: sorted(hashes)
        for dataset, hashes in dataset_hashes.items()
        if len(hashes) > 1
    }
    allowed_source_hashes = sorted(set(args.allowed_source_sha256))
    source_hashes_valid = source_hashes_are_valid(
        source_hashes,
        allowed_source_hashes,
    )
    if complete_runs and (
        len(config_hashes) != 1
        or not source_hashes_valid
        or len(kvpress_commits) != 1
    ):
        audit_status = "fail"
    if inconsistent_dataset_hashes:
        audit_status = "fail"
    audit = {
        "status": audit_status,
        "run_prefix": args.run_prefix,
        "run_directories": len(run_dirs),
        "complete_runs": sum(run["status"] == "pass" for run in audit_runs),
        "base_authority_equivalence_pairs": len(equivalence_rows),
        "base_authority_equivalence_mismatches": mismatches,
        "fullkv_authority_comparisons": len(paired_utility_rows),
        "fullkv_authority_integrity_failures": (
            paired_utility_integrity_failures
        ),
        "experiment_config_hashes": config_hashes,
        "source_hashes": source_hashes,
        "allowed_source_hashes": allowed_source_hashes,
        "source_hashes_valid": source_hashes_valid,
        "kvpress_commits": kvpress_commits,
        "inconsistent_dataset_hashes": inconsistent_dataset_hashes,
        "runs": audit_runs,
    }
    write_csv(out_dir / "utility_summary.csv", summary_rows)
    write_csv(out_dir / "base_authority_equivalence.csv", equivalence_rows)
    write_csv(
        out_dir / "paired_utility_comparisons.csv",
        paired_utility_rows,
    )
    write_json(out_dir / "data_quality_audit.json", audit)

    lines = [
        "# Official External Utility Summary",
        "",
        f"Data-quality status: **{audit_status.upper()}**.",
        "",
        (
            "Exact official-base/Authority no-span equivalence: "
            f"{len(equivalence_rows) - mismatches}/{len(equivalence_rows)} paired outputs."
        ),
        (
            "FullKV/Authority paired utility comparisons: "
            f"{len(paired_utility_rows)}."
        ),
        "",
        "| Dataset | Method | KV keep | Accuracy | LongBench score | Median prefill (s) | Median peak MB |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        score = row["longbench_score"]
        lines.append(
            "| {dataset} | `{method}` | {keep:.0%} | {correct}/{n} | {score} | {prefill} | {memory} |".format(
                dataset=Path(row["dataset"]).name,
                method=row["method"],
                keep=row["keep_ratio"],
                correct=row["utility_correct_num"],
                n=row["num_examples"],
                score=f"{score:.3f}" if score is not None else "n/a",
                prefill=(
                    f"{row['prefill_seconds_median']:.4f}"
                    if row["prefill_seconds_median"] is not None
                    else "n/a"
                ),
                memory=(
                    f"{row['peak_memory_mb_median']:.1f}"
                    if row["peak_memory_mb_median"] is not None
                    else "n/a"
                ),
            )
        )
    (out_dir / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))
    if audit_status != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
