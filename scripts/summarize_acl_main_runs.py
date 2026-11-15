#!/usr/bin/env python3
"""Audit, aggregate, and statistically compare the official ACL Main sweep."""

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
from typing import Any, Iterable


DECISION_LABELS = {
    "FOLLOW_SYSTEM",
    "FOLLOW_DEVELOPER",
    "FOLLOW_USER",
    "FOLLOW_TOOL",
    "FOLLOW_RETRIEVED_DOCUMENT",
    "ALLOW",
    "REFUSE",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", default="results/authoritykv")
    parser.add_argument(
        "--run-prefix",
        default="aclmain_20260725v1_",
        help="One prefix or a comma-separated list of run-directory prefixes.",
    )
    parser.add_argument("--out-dir", default="reports/acl_main_official")
    parser.add_argument("--bootstrap-samples", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20260530)
    parser.add_argument(
        "--protocol-amendment",
        default=None,
        help=(
            "Optional decode-cap amendment used to validate affected run "
            "IDs, config hashes and generation lengths."
        ),
    )
    parser.add_argument(
        "--allowed-source-sha256",
        action="append",
        default=[],
        help=(
            "Registered source digest accepted when a protocol amendment "
            "is active; repeat for each allowed source state."
        ),
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protocol_validation_failures(
    config: dict[str, Any],
    amendment: dict[str, Any] | None,
    amendment_sha256: str | None,
    allowed_source_sha256: set[str],
) -> list[str]:
    if amendment is None:
        return []

    replacement = amendment.get("replacement_policy", {})
    affected_suffixes = {
        str(value)
        for value in replacement.get("affected_run_suffixes", [])
    }
    run_id = str(config.get("run_id") or "")
    affected = any(run_id.endswith(suffix) for suffix in affected_suffixes)
    parent_sha256 = str(amendment.get("parent_matrix_sha256") or "")
    expected_config_sha256 = (
        amendment_sha256 if affected else parent_sha256
    )
    expected_max_new_tokens = (
        int(replacement.get("max_new_tokens", -1)) if affected else 16
    )
    failures: list[str] = []
    if config.get("experiment_config_sha256") != expected_config_sha256:
        failures.append(
            "experiment config hash does not match the registered "
            f"{'replacement' if affected else 'parent'} protocol"
        )
    if int(config.get("max_new_tokens", -1)) != expected_max_new_tokens:
        failures.append(
            "max_new_tokens does not match the registered "
            f"{'replacement' if affected else 'parent'} protocol"
        )
    if (
        allowed_source_sha256
        and str(config.get("source_sha256")) not in allowed_source_sha256
    ):
        failures.append("source digest is outside the registered allowlist")
    return failures


def read_exit_code(path: Path) -> int | None:
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def count_jsonl_rows(path: Path) -> int | None:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return sum(bool(line.strip()) for line in handle)
    except OSError:
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
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = probability * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def wilson_interval(numerator: int, denominator: int) -> tuple[float | None, float | None]:
    if denominator <= 0:
        return None, None
    z = 1.959963984540054
    proportion = numerator / denominator
    denominator_term = 1 + z * z / denominator
    center = (proportion + z * z / (2 * denominator)) / denominator_term
    margin = (
        z
        * math.sqrt(
            proportion * (1 - proportion) / denominator
            + z * z / (4 * denominator * denominator)
        )
        / denominator_term
    )
    return max(0.0, center - margin), min(1.0, center + margin)


def exact_mcnemar_p(n10: int, n01: int) -> float:
    discordant = n10 + n01
    if discordant == 0:
        return 1.0
    tail = min(n10, n01)
    probability = sum(math.comb(discordant, k) for k in range(tail + 1)) / (2**discordant)
    return min(1.0, 2 * probability)


def holm_adjust(p_values: list[float]) -> list[float]:
    """Return family-wise-error-controlled Holm adjusted p-values."""

    if not p_values:
        return []
    order = sorted(range(len(p_values)), key=p_values.__getitem__)
    adjusted = [1.0] * len(p_values)
    running_max = 0.0
    total = len(p_values)
    for rank, index in enumerate(order):
        candidate = min(1.0, (total - rank) * float(p_values[index]))
        running_max = max(running_max, candidate)
        adjusted[index] = running_max
    return adjusted


def bootstrap_delta_interval(
    pairs: list[tuple[int, int]],
    samples: int,
    rng: random.Random,
) -> tuple[float | None, float | None]:
    if not pairs or samples <= 0:
        return None, None
    count = len(pairs)
    deltas: list[float] = []
    for _ in range(samples):
        base_total = 0
        comparison_total = 0
        for _ in range(count):
            base, comparison = pairs[rng.randrange(count)]
            base_total += base
            comparison_total += comparison
        deltas.append((comparison_total - base_total) / count)
    return quantile(deltas, 0.025), quantile(deltas, 0.975)


def cluster_bootstrap_delta_interval(
    clusters: dict[str, list[tuple[int, int]]],
    samples: int,
    rng: random.Random,
) -> tuple[float | None, float | None]:
    """Bootstrap prompt clusters so cross-model replicas are not independent."""

    cluster_ids = sorted(clusters)
    if not cluster_ids or samples <= 0:
        return None, None
    deltas: list[float] = []
    for _ in range(samples):
        sampled_pairs: list[tuple[int, int]] = []
        for _ in cluster_ids:
            sampled_pairs.extend(clusters[cluster_ids[rng.randrange(len(cluster_ids))]])
        if sampled_pairs:
            deltas.append(
                sum(comparison - base for base, comparison in sampled_pairs)
                / len(sampled_pairs)
            )
    return quantile(deltas, 0.025), quantile(deltas, 0.975)


def as_float(record: dict[str, Any], field: str) -> float | None:
    value = record.get(field)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def stats(values: Iterable[float | None]) -> dict[str, float | None]:
    clean = [float(value) for value in values if value is not None]
    return {
        "median": median(clean) if clean else None,
        "q1": quantile(clean, 0.25),
        "q3": quantile(clean, 0.75),
    }


def official_base_for(method: str) -> str | None:
    if method.startswith("authority_") or method.startswith("system_") or method.startswith(
        "all_control_"
    ):
        for base in (
            "snapkv",
            "streaming",
            "knorm",
            "h2o",
            "tova",
            "pyramid",
        ):
            if f"_{base}_" in method:
                return f"kvpress_{base}"
    return None


def is_infeasible(record: dict[str, Any]) -> bool:
    """Recognize both current typed outcomes and legacy pilot error records."""

    if record.get("status") == "infeasible":
        return True
    error = str(record.get("error") or "")
    return "protected authority tokens exceed cache budget" in error


def is_eligible(record: dict[str, Any]) -> bool:
    """Return whether a scheduled cell produced a judgeable model output."""

    return (
        not is_infeasible(record)
        and record.get("status", "ok") == "ok"
        and record.get("error") is None
    )


def is_exact_json_object(text: Any) -> bool:
    """Require the complete stripped output, rather than an extracted span, to be JSON."""

    if not isinstance(text, str) or not text.strip():
        return False
    try:
        parsed = json.loads(text.strip())
    except (TypeError, ValueError, json.JSONDecodeError):
        return False
    return isinstance(parsed, dict)


def is_exact_decision_json(text: Any) -> bool:
    """Require the complete output to match the one-field decision schema."""

    if not isinstance(text, str) or not text.strip():
        return False
    try:
        parsed = json.loads(text.strip())
    except (TypeError, ValueError, json.JSONDecodeError):
        return False
    if not isinstance(parsed, dict) or set(parsed) != {"decision"}:
        return False
    decision = parsed["decision"]
    return (
        isinstance(decision, str)
        and decision.strip().upper().replace("\\_", "_") in DECISION_LABELS
    )


def group_key(record: dict[str, Any]) -> tuple[str, str, str, float]:
    return (
        str(record["model"]),
        str(record["dataset"]),
        str(record["method"]),
        float(record.get("keep_ratio", 1.0)),
    )


def summarize_group(records: list[dict[str, Any]]) -> dict[str, Any]:
    first = records[0]
    budget_feasible = [record for record in records if not is_infeasible(record)]
    eligible = [record for record in records if is_eligible(record)]
    scheduled_conflict = [record for record in records if record.get("is_conflict")]
    scheduled_benign = [record for record in records if record.get("is_benign")]
    conflict = [record for record in eligible if record.get("is_conflict")]
    benign = [record for record in eligible if record.get("is_benign")]
    conflict_correct = sum(bool(record.get("correct")) for record in conflict)
    reversals = sum(bool(record.get("authority_reversal")) for record in conflict)
    benign_correct = sum(bool(record.get("correct")) for record in benign)
    end_to_end_conflict_correct = sum(
        bool(record.get("correct")) for record in scheduled_conflict
    )
    end_to_end_benign_correct = sum(
        bool(record.get("correct")) for record in scheduled_benign
    )
    malformed = sum(bool(record.get("malformed")) for record in eligible)
    judge_json_parse = sum(bool(record.get("strict_json")) for record in eligible)
    exact_json_object = sum(
        is_exact_json_object(record.get("output_text")) for record in eligible
    )
    exact_strict_json = sum(
        is_exact_decision_json(record.get("output_text")) for record in eligible
    )
    infeasible = len(records) - len(budget_feasible)
    errors = sum(
        not is_infeasible(record) and not is_eligible(record)
        for record in records
    )
    reversal_low, reversal_high = wilson_interval(reversals, len(conflict))
    hierarchy_low, hierarchy_high = wilson_interval(conflict_correct, len(conflict))
    benign_low, benign_high = wilson_interval(benign_correct, len(benign))

    cold_index = min(
        (int(record.get("example_index", 0)) for record in eligible),
        default=0,
    )
    warmed = [
        record
        for record in eligible
        if int(record.get("example_index", 0)) != cold_index
    ]
    if not warmed:
        warmed = eligible
    prefill = stats(as_float(record, "prefill_seconds") for record in warmed)
    decode = stats(as_float(record, "decode_seconds") for record in warmed)
    elapsed = stats(as_float(record, "elapsed_seconds") for record in warmed)
    throughput = stats(as_float(record, "decode_tokens_per_second") for record in warmed)
    peak_memory = stats(as_float(record, "peak_memory_mb") for record in warmed)
    retained = stats(as_float(record, "retained_prompt_tokens") for record in warmed)
    prompt = stats(as_float(record, "prompt_tokens") for record in warmed)
    press_audits = [
        audit
        for record in warmed
        for audit in record.get("press_audit", [])
        if isinstance(audit, dict)
    ]
    protected_count = stats(
        as_float(audit, "protected_count") for audit in press_audits
    )
    protected_kept = stats(
        as_float(audit, "protected_kept_fraction") for audit in press_audits
    )
    excluded_count = stats(
        as_float(audit, "excluded_count") for audit in press_audits
    )
    excluded_kept = stats(
        as_float(audit, "excluded_kept_fraction") for audit in press_audits
    )

    return {
        "model": first["model"],
        "dataset": first["dataset"],
        "method": first["method"],
        "keep_ratio": float(first.get("keep_ratio", 1.0)),
        "num_examples": len(records),
        "attempted_num": len(records),
        "feasible_num": len(budget_feasible),
        "feasible_den": len(records),
        "feasibility_rate": len(budget_feasible) / len(records),
        "eligible_num": len(eligible),
        "eligible_rate": len(eligible) / len(records),
        "infeasible_num": infeasible,
        "conflict_num": len(conflict),
        "benign_num": len(benign),
        "hierarchy_success_num": conflict_correct,
        "hierarchy_success_den": len(conflict),
        "hierarchy_success": conflict_correct / len(conflict) if conflict else None,
        "hierarchy_success_ci95_low": hierarchy_low,
        "hierarchy_success_ci95_high": hierarchy_high,
        "authority_reversal_num": reversals,
        "authority_reversal_den": len(conflict),
        "authority_reversal_rate": reversals / len(conflict) if conflict else None,
        "authority_reversal_ci95_low": reversal_low,
        "authority_reversal_ci95_high": reversal_high,
        "benign_utility_num": benign_correct,
        "benign_utility_den": len(benign),
        "benign_utility": benign_correct / len(benign) if benign else None,
        "benign_utility_ci95_low": benign_low,
        "benign_utility_ci95_high": benign_high,
        "end_to_end_hierarchy_success_num": end_to_end_conflict_correct,
        "end_to_end_hierarchy_success_den": len(scheduled_conflict),
        "end_to_end_hierarchy_success": (
            end_to_end_conflict_correct / len(scheduled_conflict)
            if scheduled_conflict
            else None
        ),
        "end_to_end_benign_utility_num": end_to_end_benign_correct,
        "end_to_end_benign_utility_den": len(scheduled_benign),
        "end_to_end_benign_utility": (
            end_to_end_benign_correct / len(scheduled_benign)
            if scheduled_benign
            else None
        ),
        "malformed_num": malformed,
        "malformed_rate": malformed / len(eligible) if eligible else None,
        "judge_json_parse_num": judge_json_parse,
        "judge_json_parse_rate": (
            judge_json_parse / len(eligible) if eligible else None
        ),
        "exact_json_object_num": exact_json_object,
        "exact_json_object_rate": (
            exact_json_object / len(eligible) if eligible else None
        ),
        "strict_json_num": exact_strict_json,
        "strict_json_rate": (
            exact_strict_json / len(eligible) if eligible else None
        ),
        "errors": errors,
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
        "decode_seconds_median": decode["median"],
        "decode_seconds_q1": decode["q1"],
        "decode_seconds_q3": decode["q3"],
        "elapsed_seconds_median": elapsed["median"],
        "elapsed_seconds_q1": elapsed["q1"],
        "elapsed_seconds_q3": elapsed["q3"],
        "decode_tps_median": throughput["median"],
        "decode_tps_q1": throughput["q1"],
        "decode_tps_q3": throughput["q3"],
        "peak_memory_mb_median": peak_memory["median"],
        "peak_memory_mb_q1": peak_memory["q1"],
        "peak_memory_mb_q3": peak_memory["q3"],
        "protected_tokens_median": protected_count["median"],
        "protected_kept_fraction_median": protected_kept["median"],
        "excluded_tokens_median": excluded_count["median"],
        "excluded_kept_fraction_median": excluded_kept["median"],
    }


def main() -> None:
    args = parse_args()
    results_root = Path(args.results_root)
    out_dir = Path(args.out_dir)
    amendment_path = (
        Path(args.protocol_amendment)
        if args.protocol_amendment
        else None
    )
    amendment = (
        load_json(amendment_path) if amendment_path is not None else None
    )
    amendment_sha256 = (
        file_sha256(amendment_path)
        if amendment_path is not None
        else None
    )
    allowed_source_sha256 = {
        str(value) for value in args.allowed_source_sha256
    }
    prefixes = [prefix.strip() for prefix in args.run_prefix.split(",") if prefix.strip()]
    run_dirs = sorted(
        {
            path
            for prefix in prefixes
            for path in results_root.glob(f"{prefix}*")
            if path.is_dir()
        }
    )

    audit_runs: list[dict[str, Any]] = []
    all_records: list[dict[str, Any]] = []
    global_keys: set[tuple[str, str, str, float, str]] = set()
    duplicate_keys: list[tuple[str, str, str, float, str]] = []
    missing_artifacts: list[str] = []

    for run_dir in run_dirs:
        config_path = run_dir / "run_config.json"
        predictions_path = run_dir / "predictions.jsonl"
        judged_path = run_dir / "judged_predictions.jsonl"
        metrics_path = run_dir / "metrics.json"
        runner_exit_path = run_dir / "runner_exit_code.txt"
        judge_exit_path = run_dir / "judge_exit_code.txt"
        required = [
            config_path,
            predictions_path,
            judged_path,
            metrics_path,
            runner_exit_path,
            judge_exit_path,
        ]
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            missing_artifacts.extend(missing)
            audit_runs.append(
                {
                    "run_dir": str(run_dir),
                    "status": "incomplete",
                    "missing": missing,
                }
            )
            continue

        config = load_json(config_path)
        predictions = load_jsonl(predictions_path)
        judged = load_jsonl(judged_path)
        metrics = load_json(metrics_path)
        fullkv_correct_ids = {
            str(example_id)
            for example_id in metrics.get("fullkv_correct_conflict_ids", [])
        }
        fullkv_correct_benign_ids = {
            str(example_id)
            for example_id in metrics.get("fullkv_correct_benign_ids", [])
        }
        for record in judged:
            record["_fullkv_correct"] = str(record["example_id"]) in fullkv_correct_ids
            record["_fullkv_correct_benign"] = (
                str(record["example_id"]) in fullkv_correct_benign_ids
            )
        methods = [str(method) for method in config.get("methods", [])]
        ratios = [float(ratio) for ratio in config.get("keep_ratios", [])]
        num_examples = len({record["example_id"] for record in predictions})
        dataset_path = Path(str(config.get("dataset", "")))
        dataset_rows = count_jsonl_rows(dataset_path) if dataset_path else None
        configured_limit = config.get("limit")
        expected_examples = (
            min(dataset_rows, int(configured_limit))
            if dataset_rows is not None and configured_limit is not None
            else dataset_rows
        )
        combinations = sum(1 if method == "fullkv" else len(ratios) for method in methods)
        expected_rows = num_examples * combinations
        run_infeasible = sum(is_infeasible(record) for record in predictions)
        run_errors = sum(
            record.get("error") is not None and not is_infeasible(record)
            for record in predictions
        )
        local_keys = [
            (
                str(record["method"]),
                float(record.get("keep_ratio", 1.0)),
                str(record["example_id"]),
            )
            for record in predictions
        ]
        local_duplicate_count = len(local_keys) - len(set(local_keys))
        judged_keys = [
            (
                str(record["method"]),
                float(record.get("keep_ratio", 1.0)),
                str(record["example_id"]),
            )
            for record in judged
        ]
        key_set_mismatch = set(local_keys) != set(judged_keys)
        identity_mismatch = sum(
            str(record.get("run_id")) != str(config.get("run_id"))
            or str(record.get("model")) != str(config.get("model"))
            or str(record.get("dataset")) != str(config.get("dataset"))
            for record in predictions
        )
        runner_exit = read_exit_code(runner_exit_path)
        judge_exit = read_exit_code(judge_exit_path)
        protocol_failures = protocol_validation_failures(
            config,
            amendment,
            amendment_sha256,
            allowed_source_sha256,
        )
        status = "pass"
        if len(predictions) != expected_rows or len(judged) != expected_rows:
            status = "row_count_mismatch"
        if expected_examples is not None and num_examples != expected_examples:
            status = "dataset_example_count_mismatch"
        if local_duplicate_count:
            status = "duplicate_prediction_keys"
        if key_set_mismatch:
            status = "prediction_judgment_key_mismatch"
        if identity_mismatch:
            status = "record_identity_mismatch"
        if run_errors:
            status = "runtime_errors"
        if runner_exit != 0 or judge_exit != 0:
            status = "nonzero_or_missing_exit_code"
        if not config.get("end_time"):
            status = "missing_end_time"
        if protocol_failures:
            status = "protocol_mismatch"
        audit_runs.append(
            {
                "run_dir": str(run_dir),
                "run_id": config.get("run_id"),
                "model": config.get("model"),
                "dataset": config.get("dataset"),
                "methods": methods,
                "keep_ratios": ratios,
                "num_examples": num_examples,
                "dataset_rows": dataset_rows,
                "expected_examples": expected_examples,
                "expected_rows": expected_rows,
                "prediction_rows": len(predictions),
                "judged_rows": len(judged),
                "duplicate_keys": local_duplicate_count,
                "prediction_judgment_key_mismatch": key_set_mismatch,
                "identity_mismatch": identity_mismatch,
                "runner_exit_code": runner_exit,
                "judge_exit_code": judge_exit,
                "artifact_sha256": {
                    path.name: file_sha256(path)
                    for path in required
                },
                "errors": run_errors,
                "infeasible": run_infeasible,
                "has_end_time": bool(config.get("end_time")),
                "dataset_sha256": config.get("dataset_sha256"),
                "experiment_config_sha256": config.get("experiment_config_sha256"),
                "source_sha256": config.get("source_sha256"),
                "kvpress_commit": config.get("kvpress_commit"),
                "protocol_failures": protocol_failures,
                "status": status,
            }
        )
        for record in judged:
            key = (
                str(record["model"]),
                str(record["dataset"]),
                str(record["method"]),
                float(record.get("keep_ratio", 1.0)),
                str(record["example_id"]),
            )
            if key in global_keys:
                duplicate_keys.append(key)
            global_keys.add(key)
            all_records.append(record)

    grouped: dict[tuple[str, str, str, float], list[dict[str, Any]]] = defaultdict(list)
    for record in all_records:
        grouped[group_key(record)].append(record)
    summary_rows = [
        summarize_group(records)
        for _, records in sorted(grouped.items())
    ]

    category_groups: dict[
        tuple[str, str, str, float, str],
        list[dict[str, Any]],
    ] = defaultdict(list)
    for record in all_records:
        category_groups[
            (
                str(record["model"]),
                str(record["dataset"]),
                str(record["method"]),
                float(record.get("keep_ratio", 1.0)),
                str(record.get("category", "unknown")),
            )
        ].append(record)
    category_rows: list[dict[str, Any]] = []
    for key, records in sorted(category_groups.items()):
        model, dataset, method, keep_ratio, category = key
        feasible = [record for record in records if not is_infeasible(record)]
        reversals = sum(bool(record.get("authority_reversal")) for record in feasible)
        correct = sum(bool(record.get("correct")) for record in feasible)
        low, high = wilson_interval(reversals, len(feasible))
        category_rows.append(
            {
                "model": model,
                "dataset": dataset,
                "method": method,
                "keep_ratio": keep_ratio,
                "category": category,
                "num_examples": len(records),
                "feasible_num": len(feasible),
                "infeasible_num": len(records) - len(feasible),
                "correct_num": correct,
                "correct_rate": correct / len(feasible) if feasible else None,
                "authority_reversal_num": reversals,
                "authority_reversal_rate": reversals / len(feasible) if feasible else None,
                "authority_reversal_ci95_low": low,
                "authority_reversal_ci95_high": high,
                "errors": sum(
                    record.get("error") is not None and not is_infeasible(record)
                    for record in records
                ),
            }
        )

    position_groups: dict[
        tuple[str, str, str, float, str],
        list[dict[str, Any]],
    ] = defaultdict(list)
    for record in all_records:
        high_location = str(record.get("metadata", {}).get("high_location", "unknown"))
        position_groups[
            (
                str(record["model"]),
                str(record["dataset"]),
                str(record["method"]),
                float(record.get("keep_ratio", 1.0)),
                high_location,
            )
        ].append(record)
    position_rows: list[dict[str, Any]] = []
    for (model, dataset, method, keep_ratio, high_location), records in sorted(
        position_groups.items()
    ):
        feasible = [record for record in records if not is_infeasible(record)]
        conflict = [record for record in feasible if record.get("is_conflict")]
        reversals = sum(
            bool(record.get("authority_reversal")) for record in conflict
        )
        correct = sum(bool(record.get("correct")) for record in conflict)
        low, high = wilson_interval(reversals, len(conflict))
        position_rows.append(
            {
                "model": model,
                "dataset": dataset,
                "method": method,
                "keep_ratio": keep_ratio,
                "high_location": high_location,
                "conflict_num": len(conflict),
                "hierarchy_success_num": correct,
                "hierarchy_success_rate": (
                    correct / len(conflict) if conflict else None
                ),
                "authority_reversal_num": reversals,
                "authority_reversal_rate": (
                    reversals / len(conflict) if conflict else None
                ),
                "authority_reversal_ci95_low": low,
                "authority_reversal_ci95_high": high,
                "infeasible_num": len(records) - len(feasible),
            }
        )

    record_lookup = {
        (
            str(record["model"]),
            str(record["dataset"]),
            str(record["method"]),
            float(record.get("keep_ratio", 1.0)),
            str(record["example_id"]),
        ): record
        for record in all_records
    }
    fullkv_correct: dict[tuple[str, str], set[str]] = defaultdict(set)
    for record in all_records:
        if record.get("is_conflict") and (
            record.get("_fullkv_correct")
            or (record["method"] == "fullkv" and record.get("correct"))
        ):
            fullkv_correct[(str(record["model"]), str(record["dataset"]))].add(
                str(record["example_id"])
            )

    rng = random.Random(args.seed)
    paired_rows: list[dict[str, Any]] = []
    pooled_observations: dict[
        tuple[str, str, float],
        dict[str, list[tuple[int, int]]],
    ] = defaultdict(lambda: defaultdict(list))
    comparison_groups = [
        key for key in grouped if official_base_for(key[2]) is not None
    ]
    for model, dataset, comparison, keep_ratio in sorted(comparison_groups):
        base = official_base_for(comparison)
        assert base is not None
        allowed_ids = fullkv_correct.get((model, dataset), set())
        pairs: list[tuple[int, int]] = []
        for example_id in sorted(allowed_ids):
            base_record = record_lookup.get(
                (model, dataset, base, keep_ratio, example_id)
            )
            comparison_record = record_lookup.get(
                (model, dataset, comparison, keep_ratio, example_id)
            )
            if base_record is None or comparison_record is None:
                continue
            if is_infeasible(base_record) or is_infeasible(comparison_record):
                continue
            pairs.append(
                (
                    int(bool(base_record.get("authority_reversal"))),
                    int(bool(comparison_record.get("authority_reversal"))),
                )
            )
            pooled_observations[(base, comparison, keep_ratio)][example_id].append(
                pairs[-1]
            )
        if not pairs:
            continue
        base_reversals = sum(base_value for base_value, _ in pairs)
        comparison_reversals = sum(comparison_value for _, comparison_value in pairs)
        n10 = sum(base_value == 1 and comparison_value == 0 for base_value, comparison_value in pairs)
        n01 = sum(base_value == 0 and comparison_value == 1 for base_value, comparison_value in pairs)
        delta = (comparison_reversals - base_reversals) / len(pairs)
        delta_low, delta_high = bootstrap_delta_interval(
            pairs,
            args.bootstrap_samples,
            rng,
        )
        paired_rows.append(
            {
                "model": model,
                "dataset": dataset,
                "keep_ratio": keep_ratio,
                "official_base": base,
                "comparison": comparison,
                "paired_conflict_num": len(pairs),
                "base_reversal_num": base_reversals,
                "base_reversal_rate": base_reversals / len(pairs),
                "comparison_reversal_num": comparison_reversals,
                "comparison_reversal_rate": comparison_reversals / len(pairs),
                "absolute_rate_delta": delta,
                "absolute_rate_delta_ci95_low": delta_low,
                "absolute_rate_delta_ci95_high": delta_high,
                "relative_reversal_reduction": (
                    (base_reversals - comparison_reversals) / base_reversals
                    if base_reversals
                    else None
                ),
                "base_only_reversal_n10": n10,
                "comparison_only_reversal_n01": n01,
                "exact_mcnemar_p": exact_mcnemar_p(n10, n01),
            }
        )

    adjusted_p_values = holm_adjust(
        [float(row["exact_mcnemar_p"]) for row in paired_rows]
    )
    for row, adjusted_p in zip(paired_rows, adjusted_p_values):
        row["holm_adjusted_p_global_family"] = adjusted_p
        row["holm_significant_0_05"] = adjusted_p < 0.05

    # Authority reversal remains the registered primary endpoint above.
    # Secondary paired endpoints capture repairs of malformed or otherwise
    # incorrect outputs without changing the primary multiple-test family.
    fullkv_correct_benign: dict[tuple[str, str], set[str]] = defaultdict(set)
    for record in all_records:
        if record.get("is_benign") and (
            record.get("_fullkv_correct_benign")
            or (record["method"] == "fullkv" and record.get("correct"))
        ):
            fullkv_correct_benign[
                (str(record["model"]), str(record["dataset"]))
            ].add(str(record["example_id"]))
    paired_endpoint_rows: list[dict[str, Any]] = []
    endpoint_specs = [
        (
            "hierarchy_success",
            "conflict",
            lambda record: int(bool(record.get("correct"))),
        ),
        (
            "benign_utility",
            "benign",
            lambda record: int(bool(record.get("correct"))),
        ),
        (
            "strict_json",
            "all_fullkv_correct",
            lambda record: int(bool(record.get("strict_json"))),
        ),
    ]
    for model, dataset, comparison, keep_ratio in sorted(comparison_groups):
        base = official_base_for(comparison)
        assert base is not None
        conflict_ids = fullkv_correct.get((model, dataset), set())
        benign_ids = fullkv_correct_benign.get((model, dataset), set())
        for endpoint, scope, value_for in endpoint_specs:
            if scope == "conflict":
                allowed_ids = conflict_ids
            elif scope == "benign":
                allowed_ids = benign_ids
            else:
                allowed_ids = conflict_ids | benign_ids
            endpoint_pairs: list[tuple[int, int]] = []
            for example_id in sorted(allowed_ids):
                base_record = record_lookup.get(
                    (model, dataset, base, keep_ratio, example_id)
                )
                comparison_record = record_lookup.get(
                    (model, dataset, comparison, keep_ratio, example_id)
                )
                if base_record is None or comparison_record is None:
                    continue
                if is_infeasible(base_record) or is_infeasible(comparison_record):
                    continue
                endpoint_pairs.append(
                    (value_for(base_record), value_for(comparison_record))
                )
            if not endpoint_pairs:
                continue
            base_num = sum(left for left, _ in endpoint_pairs)
            comparison_num = sum(right for _, right in endpoint_pairs)
            n10 = sum(
                left == 1 and right == 0
                for left, right in endpoint_pairs
            )
            n01 = sum(
                left == 0 and right == 1
                for left, right in endpoint_pairs
            )
            delta_low, delta_high = bootstrap_delta_interval(
                endpoint_pairs,
                args.bootstrap_samples,
                rng,
            )
            raw_delta = (comparison_num - base_num) / len(endpoint_pairs)
            paired_endpoint_rows.append(
                {
                    "model": model,
                    "dataset": dataset,
                    "keep_ratio": keep_ratio,
                    "official_base": base,
                    "comparison": comparison,
                    "endpoint": endpoint,
                    "scope": scope,
                    "direction": "higher_is_better",
                    "paired_num": len(endpoint_pairs),
                    "base_num": base_num,
                    "base_rate": base_num / len(endpoint_pairs),
                    "comparison_num": comparison_num,
                    "comparison_rate": comparison_num / len(endpoint_pairs),
                    "absolute_rate_delta": raw_delta,
                    "absolute_rate_delta_ci95_low": delta_low,
                    "absolute_rate_delta_ci95_high": delta_high,
                    "favorable_rate_delta": raw_delta,
                    "base_only_success_n10": n10,
                    "comparison_only_success_n01": n01,
                    "exact_mcnemar_p": exact_mcnemar_p(n10, n01),
                }
            )
    endpoint_adjusted = holm_adjust(
        [
            float(row["exact_mcnemar_p"])
            for row in paired_endpoint_rows
        ]
    )
    for row, adjusted_p in zip(paired_endpoint_rows, endpoint_adjusted):
        row["holm_adjusted_p_secondary_family"] = adjusted_p
        row["holm_significant_0_05"] = adjusted_p < 0.05

    pooled_rows: list[dict[str, Any]] = []
    for (base, comparison, keep_ratio), clusters in sorted(
        pooled_observations.items()
    ):
        pairs = [pair for cluster in clusters.values() for pair in cluster]
        base_reversals = sum(base_value for base_value, _ in pairs)
        comparison_reversals = sum(
            comparison_value for _, comparison_value in pairs
        )
        delta = (comparison_reversals - base_reversals) / len(pairs)
        delta_low, delta_high = cluster_bootstrap_delta_interval(
            clusters,
            args.bootstrap_samples,
            rng,
        )
        pooled_rows.append(
            {
                "official_base": base,
                "comparison": comparison,
                "keep_ratio": keep_ratio,
                "paired_model_example_num": len(pairs),
                "prompt_cluster_num": len(clusters),
                "base_reversal_num": base_reversals,
                "base_reversal_rate": base_reversals / len(pairs),
                "comparison_reversal_num": comparison_reversals,
                "comparison_reversal_rate": comparison_reversals / len(pairs),
                "absolute_rate_delta": delta,
                "cluster_bootstrap_delta_ci95_low": delta_low,
                "cluster_bootstrap_delta_ci95_high": delta_high,
                "relative_reversal_reduction": (
                    (base_reversals - comparison_reversals) / base_reversals
                    if base_reversals
                    else None
                ),
                "inference_note": "Prompt-cluster bootstrap; exact tests remain model/dataset stratified.",
            }
        )

    audit_status = "pass"
    complete_runs = [run for run in audit_runs if run.get("status") == "pass"]
    experiment_config_hashes = sorted(
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
    dataset_hashes_by_path: dict[str, set[str]] = defaultdict(set)
    for run in complete_runs:
        if run.get("dataset") and run.get("dataset_sha256"):
            dataset_hashes_by_path[str(run["dataset"])].add(
                str(run["dataset_sha256"])
            )
    inconsistent_dataset_hashes = {
        path: sorted(hashes)
        for path, hashes in dataset_hashes_by_path.items()
        if len(hashes) > 1
    }
    if not run_dirs:
        audit_status = "fail"
    if missing_artifacts or duplicate_keys:
        audit_status = "fail"
    if any(run.get("status") != "pass" for run in audit_runs):
        audit_status = "fail"
    if complete_runs:
        if amendment is None:
            provenance_valid = (
                len(experiment_config_hashes) == 1
                and len(source_hashes) == 1
            )
        else:
            expected_config_hashes = {
                str(amendment.get("parent_matrix_sha256") or ""),
                str(amendment_sha256 or ""),
            }
            provenance_valid = (
                set(experiment_config_hashes) <= expected_config_hashes
                and bool(experiment_config_hashes)
                and (
                    not allowed_source_sha256
                    or set(source_hashes) <= allowed_source_sha256
                )
                and bool(source_hashes)
            )
        if not provenance_valid or len(kvpress_commits) != 1:
            audit_status = "fail"
    if inconsistent_dataset_hashes:
        audit_status = "fail"
    audit = {
        "status": audit_status,
        "run_prefix": args.run_prefix,
        "run_directories": len(run_dirs),
        "complete_runs": sum(run.get("status") == "pass" for run in audit_runs),
        "missing_artifacts": missing_artifacts,
        "global_duplicate_keys": [list(key) for key in duplicate_keys],
        "experiment_config_hashes": experiment_config_hashes,
        "source_hashes": source_hashes,
        "protocol_amendment": (
            str(amendment_path) if amendment_path is not None else None
        ),
        "protocol_amendment_sha256": amendment_sha256,
        "allowed_source_sha256": sorted(allowed_source_sha256),
        "protocol_failures": [
            {
                "run_id": run.get("run_id"),
                "failures": run.get("protocol_failures"),
            }
            for run in audit_runs
            if run.get("protocol_failures")
        ],
        "kvpress_commits": kvpress_commits,
        "inconsistent_dataset_hashes": inconsistent_dataset_hashes,
        "runs": audit_runs,
    }

    write_csv(out_dir / "method_summary.csv", summary_rows)
    write_csv(out_dir / "category_summary.csv", category_rows)
    write_csv(out_dir / "position_summary.csv", position_rows)
    write_csv(out_dir / "paired_comparisons.csv", paired_rows)
    write_csv(
        out_dir / "paired_endpoint_comparisons.csv",
        paired_endpoint_rows,
    )
    write_csv(out_dir / "pooled_cluster_comparisons.csv", pooled_rows)
    write_json(out_dir / "data_quality_audit.json", audit)

    report_lines = [
        "# ACL Main Official Sweep Summary",
        "",
        f"Data-quality status: **{audit_status.upper()}**.",
        "",
        f"Complete run directories: {audit['complete_runs']}/{audit['run_directories']}.",
        "",
        "## Method-level results",
        "",
        "| Model | Method | KV keep | Feasible | ARR | Hierarchy success | Benign utility | Errors | Median prefill (s) | Median peak MB |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        report_lines.append(
            "| {model} | `{method}` | {keep:.0%} | {feasible}/{total} | {arr} | {hier} | {benign} | "
            "{errors} | {prefill} | {memory} |".format(
                model=row["model"],
                method=row["method"],
                keep=row["keep_ratio"],
                feasible=row["feasible_num"],
                total=row["feasible_den"],
                arr=(
                    f"{row['authority_reversal_num']}/{row['authority_reversal_den']}"
                    if row["authority_reversal_den"]
                    else "n/a"
                ),
                hier=(
                    f"{row['hierarchy_success_num']}/{row['hierarchy_success_den']}"
                    if row["hierarchy_success_den"]
                    else "n/a"
                ),
                benign=(
                    f"{row['benign_utility_num']}/{row['benign_utility_den']}"
                    if row["benign_utility_den"]
                    else "n/a"
                ),
                errors=row["errors"],
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
    report_lines.extend(
        [
            "",
            "## Paired comparisons",
            "",
            "| Model | Base | Comparison | KV keep | Base ARR | Comparison ARR | Relative reduction | Exact p | Holm p |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in paired_rows:
        relative = row["relative_reversal_reduction"]
        report_lines.append(
            "| {model} | `{base}` | `{comparison}` | {keep:.0%} | {base_num}/{n} | "
            "{comparison_num}/{n} | {relative} | {p:.3g} | {holm:.3g} |".format(
                model=row["model"],
                base=row["official_base"],
                comparison=row["comparison"],
                keep=row["keep_ratio"],
                base_num=row["base_reversal_num"],
                comparison_num=row["comparison_reversal_num"],
                n=row["paired_conflict_num"],
                relative=f"{relative:.1%}" if relative is not None else "n/a",
                p=row["exact_mcnemar_p"],
                holm=row["holm_adjusted_p_global_family"],
            )
        )
    report_lines.extend(
        [
            "",
            "## Paired secondary endpoints",
            "",
            "These endpoints use a separate global Holm family; the registered "
            "authority-reversal family above is unchanged.",
            "",
            "| Model | Base | Comparison | KV keep | Endpoint | Scope | Base | Comparison | Delta | Holm p |",
            "|---|---|---|---:|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in paired_endpoint_rows:
        report_lines.append(
            "| {model} | `{base}` | `{comparison}` | {keep:.0%} | "
            "{endpoint} | {scope} | {base_num}/{n} | {comparison_num}/{n} | "
            "{delta:+.1%} | {holm:.3g} |".format(
                model=row["model"],
                base=row["official_base"],
                comparison=row["comparison"],
                keep=row["keep_ratio"],
                endpoint=row["endpoint"],
                scope=row["scope"],
                base_num=row["base_num"],
                comparison_num=row["comparison_num"],
                n=row["paired_num"],
                delta=row["absolute_rate_delta"],
                holm=row["holm_adjusted_p_secondary_family"],
            )
        )
    report_lines.extend(
        [
            "",
            "## Pooled descriptive comparisons",
            "",
            "Pooled intervals resample prompt IDs as clusters, keeping cross-model replicas together; exact tests above remain model/dataset stratified.",
            "",
            "| Base | Comparison | KV keep | Base ARR | Comparison ARR | Relative reduction | Cluster-bootstrap delta 95% CI |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in pooled_rows:
        relative = row["relative_reversal_reduction"]
        report_lines.append(
            "| `{base}` | `{comparison}` | {keep:.0%} | {base_num}/{n} | "
            "{comparison_num}/{n} | {relative} | [{low:.3f}, {high:.3f}] |".format(
                base=row["official_base"],
                comparison=row["comparison"],
                keep=row["keep_ratio"],
                base_num=row["base_reversal_num"],
                comparison_num=row["comparison_reversal_num"],
                n=row["paired_model_example_num"],
                relative=f"{relative:.1%}" if relative is not None else "n/a",
                low=row["cluster_bootstrap_delta_ci95_low"],
                high=row["cluster_bootstrap_delta_ci95_high"],
            )
        )
    (out_dir / "SUMMARY.md").write_text(
        "\n".join(report_lines) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "audit_status": audit_status,
                "runs": len(run_dirs),
                "method_rows": len(summary_rows),
                "category_rows": len(category_rows),
                "position_rows": len(position_rows),
                "paired_rows": len(paired_rows),
                "paired_endpoint_rows": len(paired_endpoint_rows),
                "pooled_rows": len(pooled_rows),
                "out_dir": str(out_dir),
            },
            indent=2,
        )
    )
    if audit_status != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
