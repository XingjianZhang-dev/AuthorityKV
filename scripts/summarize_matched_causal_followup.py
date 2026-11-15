#!/usr/bin/env python3
"""Summarize the preregistered matched authority counterfactual."""

from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path
from typing import Any

from summarize_acl_main_runs import (
    bootstrap_delta_interval,
    exact_mcnemar_p,
    holm_adjust,
    is_eligible,
    is_infeasible,
)


REPRODUCTION_FIELDS = (
    "status",
    "error",
    "infeasible_reason",
    "output_text",
    "generated_token_ids",
    "generation_tokens",
    "max_new_tokens",
    "retained_prompt_tokens",
    "retained_prompt_tokens_min",
    "retained_prompt_tokens_max",
    "press_audit",
    "authority_token_spans",
    "layerwise_mask_adapter_activated",
    "layerwise_mask_adapter_audit",
)
BUDGET_FIELDS = (
    "retained_prompt_tokens",
    "retained_prompt_tokens_min",
    "retained_prompt_tokens_max",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="configs/acl_main_matched_causal_followup.json",
    )
    parser.add_argument(
        "--run-dir",
        default=(
            "results/authoritykv/"
            "akvcausal_20260726v4_matched_long8k30"
        ),
    )
    parser.add_argument(
        "--prior-run",
        default=(
            "results/authoritykv/"
            "akvopt_20260725v3_long8k_extreme_adaptive30"
        ),
    )
    parser.add_argument(
        "--out-dir",
        default="reports/akvcausal_20260726v4_matched",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def row_key(row: dict[str, Any]) -> tuple[str, str, float]:
    return (
        str(row["example_id"]),
        str(row["method"]),
        float(row["keep_ratio"]),
    )


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def field_mismatches(
    left: dict[str, Any],
    right: dict[str, Any],
    fields: tuple[str, ...],
) -> list[str]:
    return [
        field
        for field in fields
        if left.get(field) != right.get(field)
    ]


def evaluate(
    config: dict[str, Any],
    predictions: list[dict[str, Any]],
    judged: list[dict[str, Any]],
    prior_judged: list[dict[str, Any]],
) -> dict[str, Any]:
    failures: list[str] = []
    run_cfg = config["run"]
    gates = config["registered_gates"]
    expected_methods = set(run_cfg["methods"])
    expected_ratio = float(run_cfg["keep_ratio"])
    expected_rows = int(run_cfg["expected_rows"])

    prediction_keys = [row_key(row) for row in predictions]
    judged_keys = [row_key(row) for row in judged]
    if len(predictions) != expected_rows:
        failures.append(
            f"prediction rows {len(predictions)} != {expected_rows}"
        )
    if len(set(prediction_keys)) != expected_rows:
        failures.append("prediction keys are missing or duplicated")
    if len(judged) != expected_rows:
        failures.append(
            f"judged rows {len(judged)} != {expected_rows}"
        )
    if len(set(judged_keys)) != expected_rows:
        failures.append("judged keys are missing or duplicated")
    if set(prediction_keys) != set(judged_keys):
        failures.append("prediction and judgment keys differ")
    if {str(row["method"]) for row in predictions} != expected_methods:
        failures.append("observed method set differs from registration")
    if {
        float(row["keep_ratio"]) for row in predictions
    } != {expected_ratio}:
        failures.append("observed keep ratio differs from registration")

    runtime_errors = sum(
        row.get("status") == "runtime_error"
        or row.get("error") is not None
        for row in predictions
    )
    infeasible_rows = sum(is_infeasible(row) for row in predictions)
    if runtime_errors > int(gates["runtime_errors_max"]):
        failures.append(f"runtime errors: {runtime_errors}")
    if infeasible_rows > int(gates["infeasible_rows_max"]):
        failures.append(f"infeasible rows: {infeasible_rows}")

    lookup = {row_key(row): row for row in judged}
    prior_lookup = {row_key(row): row for row in prior_judged}
    reproduction_methods = {
        method
        for method in expected_methods
        if method.startswith("kvpress_")
        or method.endswith("_v2_adaptive")
    }
    reproduction_rows = 0
    reproduction_mismatches: list[dict[str, Any]] = []
    for key, row in lookup.items():
        if key[1] not in reproduction_methods:
            continue
        prior = prior_lookup.get(key)
        if prior is None:
            reproduction_mismatches.append(
                {"key": list(key), "fields": ["missing_prior_row"]}
            )
            continue
        reproduction_rows += 1
        mismatches = field_mismatches(
            prior,
            row,
            REPRODUCTION_FIELDS,
        )
        if mismatches:
            reproduction_mismatches.append(
                {"key": list(key), "fields": mismatches}
            )
    reproduction_supported = (
        reproduction_rows == 180
        and not reproduction_mismatches
    )
    if (
        gates["require_official_and_correct_behavioral_reproduction"]
        and not reproduction_supported
    ):
        failures.append(
            "official/correct behavior did not exactly reproduce"
        )

    rng = random.Random(int(config["statistics"]["seed"]))
    bootstrap_samples = int(
        config["statistics"]["bootstrap_samples"]
    )
    comparisons: list[dict[str, Any]] = []
    for registered in config["primary_comparisons"]:
        reference = str(registered["reference"])
        comparison = str(registered["comparison"])
        pairs = [
            (
                lookup[(example_id, reference, expected_ratio)],
                lookup[(example_id, comparison, expected_ratio)],
            )
            for example_id in sorted(
                {
                    key[0]
                    for key in lookup
                    if key[1] == reference
                }
                & {
                    key[0]
                    for key in lookup
                    if key[1] == comparison
                }
            )
        ]
        conflict_pairs = [
            pair for pair in pairs if pair[0].get("is_conflict")
        ]
        benign_pairs = [
            pair for pair in pairs if pair[0].get("is_benign")
        ]
        correctness = [
            (
                int(
                    bool(left.get("correct"))
                    and is_eligible(left)
                ),
                int(
                    bool(right.get("correct"))
                    and is_eligible(right)
                ),
            )
            for left, right in conflict_pairs
        ]
        reference_correct = sum(left for left, _ in correctness)
        comparison_correct = sum(right for _, right in correctness)
        n10 = sum(
            left == 1 and right == 0
            for left, right in correctness
        )
        n01 = sum(
            left == 0 and right == 1
            for left, right in correctness
        )
        low, high = bootstrap_delta_interval(
            correctness,
            bootstrap_samples,
            rng,
        )
        benign_output_matches = sum(
            left.get("output_text") == right.get("output_text")
            for left, right in benign_pairs
        )
        benign_token_matches = sum(
            left.get("generated_token_ids")
            == right.get("generated_token_ids")
            for left, right in benign_pairs
        )
        equal_budget_pairs = sum(
            not field_mismatches(left, right, BUDGET_FIELDS)
            for left, right in pairs
        )
        comparisons.append(
            {
                "base_family": registered["base_family"],
                "reference": reference,
                "comparison": comparison,
                "keep_ratio": expected_ratio,
                "paired_examples": len(pairs),
                "paired_conflicts": len(conflict_pairs),
                "paired_benign": len(benign_pairs),
                "reference_correct_num": reference_correct,
                "comparison_correct_num": comparison_correct,
                "reference_hierarchy_success": rate(
                    reference_correct,
                    len(conflict_pairs),
                ),
                "comparison_hierarchy_success": rate(
                    comparison_correct,
                    len(conflict_pairs),
                ),
                "hierarchy_absolute_delta": rate(
                    comparison_correct - reference_correct,
                    len(conflict_pairs),
                ),
                "hierarchy_delta_ci95_low": low,
                "hierarchy_delta_ci95_high": high,
                "reference_only_correct_n10": n10,
                "comparison_only_correct_n01": n01,
                "exact_mcnemar_p": exact_mcnemar_p(n10, n01),
                "benign_exact_output_matches": benign_output_matches,
                "benign_exact_token_id_matches": benign_token_matches,
                "equal_retained_budget_pairs": equal_budget_pairs,
                "reference_runtime_errors": sum(
                    left.get("status") == "runtime_error"
                    for left, _ in pairs
                ),
                "comparison_runtime_errors": sum(
                    right.get("status") == "runtime_error"
                    for _, right in pairs
                ),
                "reference_infeasible": sum(
                    is_infeasible(left) for left, _ in pairs
                ),
                "comparison_infeasible": sum(
                    is_infeasible(right) for _, right in pairs
                ),
            }
        )

    adjusted = holm_adjust(
        [float(row["exact_mcnemar_p"]) for row in comparisons]
    )
    for row, adjusted_p in zip(comparisons, adjusted):
        row["holm_adjusted_p_global_family"] = adjusted_p
        row["holm_significant_0_05"] = adjusted_p < 0.05

    causal_supported = bool(comparisons) and all(
        row["paired_conflicts"]
        >= int(gates["paired_conflicts_per_family_min"])
        and row["paired_benign"]
        >= int(gates["paired_benign_per_family_min"])
        and (
            not gates["require_positive_hierarchy_delta"]
            or (
                row["hierarchy_absolute_delta"] is not None
                and row["hierarchy_absolute_delta"] > 0
            )
        )
        and (
            not gates[
                "require_hierarchy_delta_ci95_low_above_zero"
            ]
            or (
                row["hierarchy_delta_ci95_low"] is not None
                and row["hierarchy_delta_ci95_low"] > 0
            )
        )
        and (
            not gates["require_global_holm_significance"]
            or row["holm_significant_0_05"]
        )
        and (
            not gates["require_exact_benign_output_match"]
            or row["benign_exact_output_matches"]
            == row["paired_benign"]
        )
        and (
            not gates["require_exact_benign_token_id_match"]
            or row["benign_exact_token_id_matches"]
            == row["paired_benign"]
        )
        and (
            not gates["require_equal_retained_budget_all_examples"]
            or row["equal_retained_budget_pairs"]
            == row["paired_examples"]
        )
        and row["reference_runtime_errors"] == 0
        and row["comparison_runtime_errors"] == 0
        and row["reference_infeasible"] == 0
        and row["comparison_infeasible"] == 0
        for row in comparisons
    )
    if not causal_supported:
        failures.append(
            "one or more registered matched causal gates failed"
        )

    return {
        "status": "PASS" if not failures else "FAIL",
        "study_design": "matched_authority_counterfactual",
        "task_compatibility": config["task_compatibility"],
        "prediction_rows": len(predictions),
        "unique_prediction_keys": len(set(prediction_keys)),
        "judged_rows": len(judged),
        "runtime_errors": runtime_errors,
        "infeasible_rows": infeasible_rows,
        "official_and_correct_reproduction_rows": (
            reproduction_rows
        ),
        "official_and_correct_reproduction_mismatches": (
            reproduction_mismatches
        ),
        "official_and_correct_reproduction_supported": (
            reproduction_supported
        ),
        "comparisons": comparisons,
        "causal_authority_selection_supported": causal_supported,
        "claim_guardrail": config["claim_guardrail"],
        "failures": failures,
    }


def main() -> None:
    args = parse_args()
    config = load_json(Path(args.config))
    run_dir = Path(args.run_dir)
    prior_run = Path(args.prior_run)
    required = [
        run_dir / "run_config.json",
        run_dir / "predictions.jsonl",
        run_dir / "judged_predictions.jsonl",
        run_dir / "metrics.json",
        run_dir / "runner_exit_code.txt",
        run_dir / "judge_exit_code.txt",
        prior_run / "judged_predictions.jsonl",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit(f"missing artifacts: {missing}")
    if (
        (run_dir / "runner_exit_code.txt").read_text().strip()
        != "0"
        or (run_dir / "judge_exit_code.txt").read_text().strip()
        != "0"
    ):
        raise SystemExit("generation or judgment exit code is nonzero")

    report = evaluate(
        config,
        load_jsonl(run_dir / "predictions.jsonl"),
        load_jsonl(run_dir / "judged_predictions.jsonl"),
        load_jsonl(prior_run / "judged_predictions.jsonl"),
    )
    run_config = load_json(run_dir / "run_config.json")
    report["run_id"] = run_config.get("run_id")
    report["source_sha256"] = run_config.get("source_sha256")
    report["experiment_config_sha256"] = run_config.get(
        "experiment_config_sha256"
    )
    report["end_time"] = run_config.get("end_time")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    write_csv(out_dir / "paired_comparisons.csv", report["comparisons"])
    lines = [
        "# Matched causal authority-selection follow-up",
        "",
        f"- Audit: {report['status']}",
        (
            "- Causal authority selection supported: "
            f"{report['causal_authority_selection_supported']}"
        ),
        (
            "- Prior official/correct rows reproduced exactly: "
            f"{report['official_and_correct_reproduction_rows']}/180"
        ),
        "",
        "| Base | Wrong→correct hierarchy | Delta (95% CI) | Holm p | Benign exact |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in report["comparisons"]:
        lines.append(
            f"| {row['base_family']} | "
            f"{row['reference_hierarchy_success']:.3f} → "
            f"{row['comparison_hierarchy_success']:.3f} | "
            f"{row['hierarchy_absolute_delta']:+.3f} "
            f"({row['hierarchy_delta_ci95_low']:+.3f}, "
            f"{row['hierarchy_delta_ci95_high']:+.3f}) | "
            f"{row['holm_adjusted_p_global_family']:.4g} | "
            f"{row['benign_exact_output_matches']}/"
            f"{row['paired_benign']} |"
        )
    (out_dir / "SUMMARY.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "out_dir": str(out_dir),
                "status": report["status"],
            },
            sort_keys=True,
        )
    )
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
