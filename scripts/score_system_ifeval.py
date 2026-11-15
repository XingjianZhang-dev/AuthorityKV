#!/usr/bin/env python3
"""Score frozen System-IFEval generations with the official public grader."""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", nargs="+", required=True)
    parser.add_argument(
        "--labels",
        default=str(ROOT / "data/external_system_ifeval/sys_ifeval_labels.jsonl"),
    )
    parser.add_argument(
        "--grader-root",
        default=str(ROOT / "external/system_ifeval"),
    )
    parser.add_argument("--out", required=True)
    parser.add_argument("--judgments-out", default=None)
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def method_key(row: dict[str, Any]) -> str:
    return f"{row['method']}@{float(row['keep_ratio']):.2f}"


def wilson_interval(successes: int, total: int) -> list[float] | None:
    if total == 0:
        return None
    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    radius = (
        z
        * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total))
        / denominator
    )
    return [max(0.0, center - radius), min(1.0, center + radius)]


def exact_mcnemar_pvalue(base_only: int, authority_only: int) -> float:
    discordant = base_only + authority_only
    if discordant == 0:
        return 1.0
    tail = min(base_only, authority_only)
    one_sided = sum(
        math.comb(discordant, index) for index in range(tail + 1)
    ) / (2**discordant)
    return min(1.0, 2.0 * one_sided)


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def paired_comparison(
    base_rows: list[dict[str, Any]],
    authority_rows: list[dict[str, Any]],
    allowed_ids: set[str] | None,
    seed: int = 20260726,
) -> dict[str, Any]:
    base = {
        row["example_id"]: row
        for row in base_rows
        if allowed_ids is None or row["example_id"] in allowed_ids
    }
    authority = {
        row["example_id"]: row
        for row in authority_rows
        if allowed_ids is None or row["example_id"] in allowed_ids
    }
    common = sorted(set(base) & set(authority))
    if not common:
        return {"pairs": 0}
    base_only = sum(
        base[key]["prompt_strict"] and not authority[key]["prompt_strict"]
        for key in common
    )
    authority_only = sum(
        authority[key]["prompt_strict"] and not base[key]["prompt_strict"]
        for key in common
    )
    both = sum(
        base[key]["prompt_strict"] and authority[key]["prompt_strict"]
        for key in common
    )
    neither = len(common) - base_only - authority_only - both
    instruction_deltas = [
        (
            sum(authority[key]["instruction_strict"])
            / len(authority[key]["instruction_strict"])
        )
        - (
            sum(base[key]["instruction_strict"])
            / len(base[key]["instruction_strict"])
        )
        for key in common
    ]
    rng = random.Random(seed)
    bootstrap_means = []
    for _ in range(5000):
        sample = [rng.randrange(len(common)) for _ in common]
        bootstrap_means.append(
            sum(instruction_deltas[index] for index in sample) / len(sample)
        )
    return {
        "pairs": len(common),
        "prompt_strict": {
            "base_only": base_only,
            "authority_only": authority_only,
            "both": both,
            "neither": neither,
            "authority_minus_base": (authority_only - base_only) / len(common),
            "mcnemar_exact_two_sided_p": exact_mcnemar_pvalue(
                base_only, authority_only
            ),
        },
        "instruction_strict": {
            "authority_minus_base": (
                sum(instruction_deltas) / len(instruction_deltas)
            ),
            "paired_prompt_bootstrap95": [
                percentile(bootstrap_means, 0.025),
                percentile(bootstrap_means, 0.975),
            ],
            "bootstrap_samples": 5000,
            "bootstrap_seed": seed,
        },
    }


def assert_paired_consistency(
    all_metrics: dict[str, Any],
    paired_comparisons: dict[str, Any],
) -> None:
    """Reject scorer outputs whose paired cells disagree with aggregates."""
    for pair_key, scopes in paired_comparisons.items():
        base_key, authority_key = pair_key.split("_vs_", 1)
        for scope, paired in scopes.items():
            prompt = paired["prompt_strict"]
            base_from_pairs = prompt["base_only"] + prompt["both"]
            authority_from_pairs = prompt["authority_only"] + prompt["both"]
            base_aggregate = all_metrics[base_key][scope]["prompt_strict_num"]
            authority_aggregate = all_metrics[authority_key][scope][
                "prompt_strict_num"
            ]
            if (
                base_from_pairs != base_aggregate
                or authority_from_pairs != authority_aggregate
            ):
                raise RuntimeError(
                    "paired/aggregate prompt-strict mismatch: "
                    f"{pair_key} {scope}; paired=({base_from_pairs},"
                    f"{authority_from_pairs}) aggregate=({base_aggregate},"
                    f"{authority_aggregate})"
                )


def score_group(
    rows: Iterable[dict[str, Any]],
    labels: dict[str, dict[str, Any]],
    evaluator: Any,
    allowed_ids: set[str] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    judgments: list[dict[str, Any]] = []
    per_family: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "strict_correct": 0,
            "loose_correct": 0,
            "total": 0,
        }
    )
    prompt_strict = prompt_loose = 0
    instruction_strict = instruction_loose = instruction_total = 0

    for row in rows:
        example_id = str(row["example_id"])
        if allowed_ids is not None and example_id not in allowed_ids:
            continue
        label = labels[example_id]
        inp = evaluator.InputExample(
            key=int(label["key"]),
            instruction_id_list=label["instruction_id_list"],
            messages=label["messages"],
            kwargs=label["kwargs"],
        )
        response = str(row.get("output_text", ""))
        response_by_key = {inp.key: response}
        strict = evaluator.test_instruction_following_strict(inp, response_by_key)
        loose = evaluator.test_instruction_following_loose(inp, response_by_key)
        prompt_strict += int(strict.follow_all_instructions)
        prompt_loose += int(loose.follow_all_instructions)
        instruction_strict += sum(strict.follow_instruction_list)
        instruction_loose += sum(loose.follow_instruction_list)
        instruction_total += len(strict.follow_instruction_list)
        for index, instruction_id in enumerate(inp.instruction_id_list):
            family = instruction_id.split(":", 1)[0]
            family_row = per_family[family]
            family_row["strict_correct"] += int(
                strict.follow_instruction_list[index]
            )
            family_row["loose_correct"] += int(loose.follow_instruction_list[index])
            family_row["total"] += 1
        judgments.append(
            {
                "example_id": example_id,
                "method": row["method"],
                "keep_ratio": row["keep_ratio"],
                "status": row.get("status"),
                "prompt_strict": strict.follow_all_instructions,
                "prompt_loose": loose.follow_all_instructions,
                "instruction_strict": strict.follow_instruction_list,
                "instruction_loose": loose.follow_instruction_list,
                "instruction_ids": inp.instruction_id_list,
            }
        )

    prompt_total = len(judgments)
    metrics = {
        "prompt_strict": prompt_strict / prompt_total if prompt_total else None,
        "prompt_strict_num": prompt_strict,
        "prompt_strict_den": prompt_total,
        "prompt_strict_wilson95": wilson_interval(prompt_strict, prompt_total),
        "prompt_loose": prompt_loose / prompt_total if prompt_total else None,
        "prompt_loose_num": prompt_loose,
        "prompt_loose_den": prompt_total,
        "prompt_loose_wilson95": wilson_interval(prompt_loose, prompt_total),
        "instruction_strict": (
            instruction_strict / instruction_total if instruction_total else None
        ),
        "instruction_strict_num": instruction_strict,
        "instruction_strict_den": instruction_total,
        "instruction_strict_wilson95": wilson_interval(
            instruction_strict, instruction_total
        ),
        "instruction_loose": (
            instruction_loose / instruction_total if instruction_total else None
        ),
        "instruction_loose_num": instruction_loose,
        "instruction_loose_den": instruction_total,
        "instruction_loose_wilson95": wilson_interval(
            instruction_loose, instruction_total
        ),
        "runtime_errors": sum(
            judgment["status"] != "ok" for judgment in judgments
        ),
        "by_instruction_family": {
            family: {
                **counts,
                "strict": counts["strict_correct"] / counts["total"],
                "loose": counts["loose_correct"] / counts["total"],
            }
            for family, counts in sorted(per_family.items())
        },
    }
    return metrics, judgments


def main() -> None:
    args = parse_args()
    predictions: list[dict[str, Any]] = []
    for path in args.predictions:
        predictions.extend(load_jsonl(Path(path)))
    labels_list = load_jsonl(Path(args.labels))
    labels = {str(row["id"]): row for row in labels_list}
    unknown = sorted(
        {str(row["example_id"]) for row in predictions} - set(labels)
    )
    if unknown:
        raise SystemExit(f"predictions contain {len(unknown)} unknown example ids")
    seen_cells: set[tuple[str, str, float]] = set()
    for row in predictions:
        cell = (
            str(row["example_id"]),
            str(row["method"]),
            float(row["keep_ratio"]),
        )
        if cell in seen_cells:
            raise SystemExit(
                "duplicate prediction cell across input files: "
                f"example={cell[0]} method={cell[1]} keep_ratio={cell[2]:.2f}"
            )
        seen_cells.add(cell)

    grader_root = str(Path(args.grader_root))
    if grader_root not in sys.path:
        sys.path.insert(0, grader_root)
    # The official grader uses langdetect for response-language constraints.
    # Its default detector factory is stochastic, so repeated scoring can
    # otherwise disagree by one or more prompts. Fix both random sources before
    # any judgment and verify paired counts against aggregate counts below.
    random.seed(0)
    from langdetect import DetectorFactory

    DetectorFactory.seed = 0
    from ifeval import evaluate as evaluator

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in predictions:
        grouped[method_key(row)].append(row)

    all_metrics: dict[str, Any] = {}
    all_judgments: list[dict[str, Any]] = []
    fullkv_rows = grouped.get("fullkv@1.00")
    if not fullkv_rows:
        raise SystemExit("a FullKV group is required for the capability gate")
    fullkv_metrics, fullkv_judgments = score_group(
        fullkv_rows, labels, evaluator
    )
    fullkv_correct_ids = {
        row["example_id"] for row in fullkv_judgments if row["prompt_strict"]
    }

    for key, rows in sorted(grouped.items()):
        metrics, judgments = score_group(rows, labels, evaluator)
        gated_metrics, _ = score_group(
            rows,
            labels,
            evaluator,
            allowed_ids=fullkv_correct_ids,
        )
        all_metrics[key] = {
            "all_prompts": metrics,
            "fullkv_strict_correct_prompts": gated_metrics,
        }
        all_judgments.extend(judgments)

    judgments_by_cell: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for judgment in all_judgments:
        judgments_by_cell[
            f"{judgment['method']}@{float(judgment['keep_ratio']):.2f}"
        ].append(judgment)
    paired_comparisons: dict[str, Any] = {}
    for key, authority_rows in sorted(judgments_by_cell.items()):
        method, ratio_text = key.rsplit("@", 1)
        if not method.startswith("authority_"):
            continue
        family = method.split("_", 2)[1]
        base_key = f"kvpress_{family}@{ratio_text}"
        base_rows = judgments_by_cell.get(base_key, [])
        if not base_rows:
            continue
        paired_comparisons[f"{base_key}_vs_{key}"] = {
            "all_prompts": paired_comparison(
                base_rows, authority_rows, None
            ),
            "fullkv_strict_correct_prompts": paired_comparison(
                base_rows,
                authority_rows,
                fullkv_correct_ids,
            ),
        }
    assert_paired_consistency(all_metrics, paired_comparisons)

    payload = {
        "benchmark": "System-IFEval",
        "official_grader": True,
        "grader_determinism": {
            "python_random_seed": 0,
            "langdetect_detector_factory_seed": 0,
            "paired_aggregate_consistency": True,
        },
        "generation_label_isolation": True,
        "fullkv_capability_gate": {
            "criterion": "prompt-level strict success under FullKV",
            "correct_ids": len(fullkv_correct_ids),
            "all_ids": len(fullkv_judgments),
            "fullkv_metrics": fullkv_metrics,
        },
        "by_method": all_metrics,
        "paired_comparisons": paired_comparisons,
        "prediction_rows": len(predictions),
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    judgments_path = (
        Path(args.judgments_out)
        if args.judgments_out
        else out_path.with_name("system_ifeval_judgments.jsonl")
    )
    with judgments_path.open("w", encoding="utf-8") as handle:
        for judgment in all_judgments:
            handle.write(json.dumps(judgment, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
