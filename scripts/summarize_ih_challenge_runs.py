#!/usr/bin/env python3
"""Audit and compare official KVPress methods on adapted IH-Challenge runs."""

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
    bootstrap_delta_interval,
    exact_mcnemar_p,
    holm_adjust,
    quantile,
    wilson_interval,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", default="results/authoritykv")
    parser.add_argument("--run-prefix", required=True)
    parser.add_argument("--out-dir", default="reports/ih_challenge_official")
    parser.add_argument("--bootstrap-samples", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20260530)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


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


def official_base_for(method: str) -> str | None:
    if not method.startswith(("authority_", "system_", "all_control_")):
        return None
    for base in ("snapkv", "streaming", "knorm", "h2o"):
        if f"_{base}_" in method:
            return f"kvpress_{base}"
    return None


def is_infeasible(record: dict[str, Any]) -> bool:
    return record.get("status") == "infeasible"


def is_eligible(record: dict[str, Any]) -> bool:
    return (
        record.get("status", "ok") == "ok"
        and record.get("error") is None
        and record.get("grader_error") is None
    )


def distribution(values: list[float]) -> dict[str, float | None]:
    return {
        "median": median(values) if values else None,
        "q1": quantile(values, 0.25),
        "q3": quantile(values, 0.75),
    }


def numeric(records: list[dict[str, Any]], field: str) -> list[float]:
    values: list[float] = []
    for record in records:
        value = record.get(field)
        if value is not None:
            values.append(float(value))
    return values


def summarize_group(
    records: list[dict[str, Any]],
    fullkv_correct_ids: set[str] | None = None,
) -> dict[str, Any]:
    first = records[0]
    eligible = [record for record in records if is_eligible(record)]
    correct_all = sum(bool(record.get("official_correct")) for record in records)
    correct_eligible = sum(
        bool(record.get("official_correct")) for record in eligible
    )
    injection_all = sum(
        bool(record.get("injection_followed")) for record in records
    )
    infeasible = sum(is_infeasible(record) for record in records)
    runtime_errors = sum(
        record.get("status") == "runtime_error" or record.get("error") is not None
        for record in records
    )
    grader_errors = sum(record.get("grader_error") is not None for record in records)
    correctness_low, correctness_high = wilson_interval(
        correct_eligible,
        len(eligible),
    )
    injection_low, injection_high = wilson_interval(
        injection_all,
        len(records),
    )

    warmed = [
        record
        for record in eligible
        if int(record.get("example_index", 0)) != 0
    ] or eligible
    prefill = distribution(numeric(warmed, "prefill_seconds"))
    elapsed = distribution(numeric(warmed, "elapsed_seconds"))
    peak = distribution(numeric(warmed, "peak_memory_mb"))
    retained = distribution(numeric(warmed, "retained_prompt_tokens"))
    prompt = distribution(numeric(warmed, "prompt_tokens"))
    audits = [
        audit
        for record in warmed
        for audit in record.get("press_audit", [])
        if isinstance(audit, dict)
    ]
    protected_kept = distribution(
        numeric(audits, "protected_kept_fraction")
    )
    excluded_kept = distribution(numeric(audits, "excluded_kept_fraction"))
    fullkv_filtered = (
        [
            record
            for record in eligible
            if str(record["example_id"]) in fullkv_correct_ids
        ]
        if fullkv_correct_ids is not None
        else []
    )
    fullkv_filtered_correct = sum(
        bool(record.get("official_correct"))
        for record in fullkv_filtered
    )

    return {
        "model": first["model"],
        "dataset": first["dataset"],
        "method": first["method"],
        "keep_ratio": float(first.get("keep_ratio", 1.0)),
        "attempted_num": len(records),
        "eligible_num": len(eligible),
        "infeasible_num": infeasible,
        "feasibility_rate": (
            (len(records) - infeasible) / len(records) if records else None
        ),
        "end_to_end_accuracy_num": correct_all,
        "end_to_end_accuracy_den": len(records),
        "end_to_end_accuracy": correct_all / len(records) if records else None,
        "conditional_accuracy_num": correct_eligible,
        "conditional_accuracy_den": len(eligible),
        "conditional_accuracy": (
            correct_eligible / len(eligible) if eligible else None
        ),
        "conditional_accuracy_ci95_low": correctness_low,
        "conditional_accuracy_ci95_high": correctness_high,
        "fullkv_correct_pool_num": (
            len(fullkv_correct_ids)
            if fullkv_correct_ids is not None
            else None
        ),
        "fullkv_filtered_accuracy_num": (
            fullkv_filtered_correct
            if fullkv_correct_ids is not None
            else None
        ),
        "fullkv_filtered_accuracy_den": (
            len(fullkv_filtered)
            if fullkv_correct_ids is not None
            else None
        ),
        "fullkv_filtered_accuracy": (
            fullkv_filtered_correct / len(fullkv_filtered)
            if fullkv_filtered
            else None
        ),
        "injection_follow_num": injection_all,
        "injection_follow_den": len(records),
        "injection_follow_rate": (
            injection_all / len(records) if records else None
        ),
        "injection_follow_ci95_low": injection_low,
        "injection_follow_ci95_high": injection_high,
        "runtime_error_num": runtime_errors,
        "grader_error_num": grader_errors,
        "prompt_tokens_median": prompt["median"],
        "retained_tokens_median": retained["median"],
        "actual_keep_ratio_median": (
            retained["median"] / prompt["median"]
            if retained["median"] is not None and prompt["median"]
            else None
        ),
        "prefill_seconds_median": prefill["median"],
        "prefill_seconds_q1": prefill["q1"],
        "prefill_seconds_q3": prefill["q3"],
        "elapsed_seconds_median": elapsed["median"],
        "elapsed_seconds_q1": elapsed["q1"],
        "elapsed_seconds_q3": elapsed["q3"],
        "peak_memory_mb_median": peak["median"],
        "peak_memory_mb_q1": peak["q1"],
        "peak_memory_mb_q3": peak["q3"],
        "protected_kept_fraction_median": protected_kept["median"],
        "excluded_kept_fraction_median": excluded_kept["median"],
    }


def paired_comparison(
    base_records: list[dict[str, Any]],
    comparison_records: list[dict[str, Any]],
    bootstrap_samples: int,
    rng: random.Random,
    eligible_example_ids: set[str] | None = None,
) -> dict[str, Any] | None:
    base = {str(record["example_id"]): record for record in base_records}
    comparison = {
        str(record["example_id"]): record for record in comparison_records
    }
    example_ids = sorted(set(base) & set(comparison))
    pairs: list[tuple[int, int]] = []
    for example_id in example_ids:
        if (
            eligible_example_ids is not None
            and example_id not in eligible_example_ids
        ):
            continue
        base_record = base[example_id]
        comparison_record = comparison[example_id]
        if not is_eligible(base_record) or not is_eligible(comparison_record):
            continue
        pairs.append(
            (
                int(bool(base_record.get("official_correct"))),
                int(bool(comparison_record.get("official_correct"))),
            )
        )
    if not pairs:
        return None
    base_correct = sum(left for left, _ in pairs)
    comparison_correct = sum(right for _, right in pairs)
    base_only = sum(left == 1 and right == 0 for left, right in pairs)
    comparison_only = sum(left == 0 and right == 1 for left, right in pairs)
    low, high = bootstrap_delta_interval(pairs, bootstrap_samples, rng)
    base_errors = len(pairs) - base_correct
    comparison_errors = len(pairs) - comparison_correct
    return {
        "paired_num": len(pairs),
        "paired_scope": (
            "fullkv_correct_and_jointly_eligible"
            if eligible_example_ids is not None
            else "jointly_eligible"
        ),
        "fullkv_correct_pool_num": (
            len(eligible_example_ids)
            if eligible_example_ids is not None
            else None
        ),
        "base_correct_num": base_correct,
        "base_accuracy": base_correct / len(pairs),
        "comparison_correct_num": comparison_correct,
        "comparison_accuracy": comparison_correct / len(pairs),
        "absolute_accuracy_delta": (
            comparison_correct - base_correct
        )
        / len(pairs),
        "absolute_accuracy_delta_ci95_low": low,
        "absolute_accuracy_delta_ci95_high": high,
        "relative_error_reduction": (
            (base_errors - comparison_errors) / base_errors
            if base_errors
            else None
        ),
        "base_only_correct_n10": base_only,
        "comparison_only_correct_n01": comparison_only,
        "exact_mcnemar_p": exact_mcnemar_p(base_only, comparison_only),
    }


def main() -> None:
    args = parse_args()
    results_root = Path(args.results_root)
    out_dir = Path(args.out_dir)
    prefixes = [
        prefix.strip() for prefix in args.run_prefix.split(",") if prefix.strip()
    ]
    run_dirs = sorted(
        {
            path
            for prefix in prefixes
            for path in results_root.glob(f"{prefix}*")
            if path.is_dir()
        }
    )

    all_records: list[dict[str, Any]] = []
    audit_runs: list[dict[str, Any]] = []
    global_keys: set[tuple[str, str, str, float, str]] = set()
    duplicates: list[tuple[str, str, str, float, str]] = []
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
        records = load_jsonl(predictions_path)
        methods = [str(method) for method in config.get("methods", [])]
        ratios = [float(ratio) for ratio in config.get("keep_ratios", [])]
        examples = len({str(record["example_id"]) for record in records})
        configured_examples = int(config.get("dataset_rows", 0))
        combinations = sum(
            1 if method == "fullkv" else len(ratios) for method in methods
        )
        expected = configured_examples * combinations
        local_keys = [
            (
                str(record["method"]),
                float(record.get("keep_ratio", 1.0)),
                str(record["example_id"]),
            )
            for record in records
        ]
        runtime_errors = sum(
            record.get("status") == "runtime_error"
            or record.get("error") is not None
            for record in records
        )
        grader_errors = sum(
            record.get("grader_error") is not None for record in records
        )
        identity_mismatch = sum(
            str(record.get("run_id")) != str(config.get("run_id"))
            or str(record.get("model")) != str(config.get("model"))
            or str(record.get("dataset")) != str(config.get("dataset"))
            for record in records
        )
        role_modes = sorted(
            {
                str(record.get("role_compatibility_mode"))
                for record in records
            }
        )
        native_primary_role_mismatch = (
            str(config.get("dataset", "")).endswith(
                "ih_challenge_blue_team_auto_quoted_system_40.jsonl"
            )
            and role_modes != ["native_roles"]
        )
        runner_exit = read_exit_code(exit_path)
        status = "pass"
        if len(records) != expected:
            status = "row_count_mismatch"
        if examples != configured_examples:
            status = "dataset_example_count_mismatch"
        if len(local_keys) != len(set(local_keys)):
            status = "duplicate_prediction_keys"
        if identity_mismatch:
            status = "record_identity_mismatch"
        if native_primary_role_mismatch:
            status = "native_primary_role_rendering_mismatch"
        if runtime_errors or grader_errors:
            status = "errors"
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
                "configured_examples": configured_examples,
                "expected_rows": expected,
                "prediction_rows": len(records),
                "runtime_errors": runtime_errors,
                "grader_errors": grader_errors,
                "identity_mismatch": identity_mismatch,
                "role_compatibility_modes": role_modes,
                "native_primary_role_mismatch": native_primary_role_mismatch,
                "runner_exit_code": runner_exit,
                "infeasible": sum(is_infeasible(record) for record in records),
                "source_sha256": config.get("source_sha256"),
                "dataset_sha256": config.get("dataset_sha256"),
                "experiment_config_sha256": config.get(
                    "experiment_config_sha256"
                ),
                "kvpress_commit": config.get("kvpress_commit"),
                "has_end_time": bool(config.get("end_time")),
                "status": status,
            }
        )
        for record in records:
            key = (
                str(record["model"]),
                str(record["dataset"]),
                str(record["method"]),
                float(record.get("keep_ratio", 1.0)),
                str(record["example_id"]),
            )
            if key in global_keys:
                duplicates.append(key)
            global_keys.add(key)
            all_records.append(record)

    groups: dict[
        tuple[str, str, str, float],
        list[dict[str, Any]],
    ] = defaultdict(list)
    for record in all_records:
        groups[
            (
                str(record["model"]),
                str(record["dataset"]),
                str(record["method"]),
                float(record.get("keep_ratio", 1.0)),
            )
        ].append(record)
    fullkv_correct: dict[tuple[str, str], set[str]] = {}
    for (model, dataset, method, keep_ratio), records in groups.items():
        if method != "fullkv" or keep_ratio != 1.0:
            continue
        fullkv_correct[(model, dataset)] = {
            str(record["example_id"])
            for record in records
            if is_eligible(record)
            and bool(record.get("official_correct"))
        }
    method_rows = [
        summarize_group(
            records,
            fullkv_correct.get((model, dataset)),
        )
        for (model, dataset, _, _), records in sorted(groups.items())
    ]

    rng = random.Random(args.seed)
    paired_rows: list[dict[str, Any]] = []
    missing_fullkv_filters: list[tuple[str, str, str, float]] = []
    for (model, dataset, method, keep_ratio), comparison_records in sorted(
        groups.items()
    ):
        official_base = official_base_for(method)
        if official_base is None:
            continue
        base_records = groups.get((model, dataset, official_base, keep_ratio))
        if not base_records:
            continue
        fullkv_ids = fullkv_correct.get((model, dataset))
        if fullkv_ids is None:
            missing_fullkv_filters.append(
                (model, dataset, method, keep_ratio)
            )
            continue
        paired = paired_comparison(
            base_records,
            comparison_records,
            args.bootstrap_samples,
            rng,
            eligible_example_ids=fullkv_ids,
        )
        if paired is not None:
            paired_rows.append(
                {
                    "model": model,
                    "dataset": dataset,
                    "keep_ratio": keep_ratio,
                    "official_base": official_base,
                    "comparison": method,
                    **paired,
                }
            )

    adjusted_p_values = holm_adjust(
        [float(row["exact_mcnemar_p"]) for row in paired_rows]
    )
    for row, adjusted_p in zip(paired_rows, adjusted_p_values):
        row["holm_adjusted_p_global_family"] = adjusted_p
        row["holm_significant_0_05"] = adjusted_p < 0.05

    audit_status = "pass"
    if not run_dirs or duplicates:
        audit_status = "fail"
    if missing_fullkv_filters:
        audit_status = "fail"
    if any(run.get("status") != "pass" for run in audit_runs):
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
    if complete_runs and (
        len(config_hashes) != 1
        or len(source_hashes) != 1
        or len(kvpress_commits) != 1
    ):
        audit_status = "fail"
    if inconsistent_dataset_hashes:
        audit_status = "fail"
    audit = {
        "status": audit_status,
        "run_prefix": args.run_prefix,
        "run_directories": len(run_dirs),
        "complete_runs": sum(run.get("status") == "pass" for run in audit_runs),
        "global_duplicate_keys": [list(key) for key in duplicates],
        "missing_fullkv_filters": [
            list(key) for key in missing_fullkv_filters
        ],
        "experiment_config_hashes": config_hashes,
        "source_hashes": source_hashes,
        "kvpress_commits": kvpress_commits,
        "inconsistent_dataset_hashes": inconsistent_dataset_hashes,
        "runs": audit_runs,
    }
    write_json(out_dir / "data_quality_audit.json", audit)
    write_csv(out_dir / "method_summary.csv", method_rows)
    write_csv(out_dir / "paired_comparisons.csv", paired_rows)

    lines = [
        "# IH-Challenge Official KVPress Summary",
        "",
        f"Data-quality status: **{audit_status.upper()}**.",
        "",
        "Accuracy uses the preserved official grader. End-to-end accuracy includes "
        "infeasible and error outcomes; conditional accuracy includes only successfully "
        "executed, gradable pairs.",
        "",
        "| Model | Method | KV keep | Eligible | End-to-end acc. | Conditional acc. | Injection follow | Infeasible | Errors |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in method_rows:
        lines.append(
            "| {model} | `{method}` | {keep:.0%} | {eligible}/{attempted} | "
            "{e2e_num}/{e2e_den} | {cond_num}/{cond_den} | {inj_num}/{inj_den} | "
            "{infeasible} | {errors} |".format(
                model=row["model"],
                method=row["method"],
                keep=row["keep_ratio"],
                eligible=row["eligible_num"],
                attempted=row["attempted_num"],
                e2e_num=row["end_to_end_accuracy_num"],
                e2e_den=row["end_to_end_accuracy_den"],
                cond_num=row["conditional_accuracy_num"],
                cond_den=row["conditional_accuracy_den"],
                inj_num=row["injection_follow_num"],
                inj_den=row["injection_follow_den"],
                infeasible=row["infeasible_num"],
                errors=row["runtime_error_num"] + row["grader_error_num"],
            )
        )
    lines.extend(
        [
            "",
            "## Paired comparisons",
            "",
            "| Model | Base | Comparison | KV keep | Base acc. | Comparison acc. | Delta | Exact p | Holm p |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in paired_rows:
        lines.append(
            "| {model} | `{base}` | `{comparison}` | {keep:.0%} | "
            "{base_num}/{n} | {comparison_num}/{n} | {delta:+.1%} | {p:.3g} | {holm:.3g} |".format(
                model=row["model"],
                base=row["official_base"],
                comparison=row["comparison"],
                keep=row["keep_ratio"],
                base_num=row["base_correct_num"],
                comparison_num=row["comparison_correct_num"],
                n=row["paired_num"],
                delta=row["absolute_accuracy_delta"],
                p=row["exact_mcnemar_p"],
                holm=row["holm_adjusted_p_global_family"],
            )
        )
    (out_dir / "SUMMARY.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "audit_status": audit_status,
                "run_directories": len(run_dirs),
                "method_rows": len(method_rows),
                "paired_rows": len(paired_rows),
                "out_dir": str(out_dir),
            },
            indent=2,
        )
    )
    if audit_status != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
