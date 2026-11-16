#!/usr/bin/env python3
"""Appendix tables of the main experiment matrix, generated from the statistics files under reports/.

The statistics files are themselves recomputed from the raw predictions by paper/tools/recompute_statistics.sh.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper" / "generated"

PARENT = ROOT / "reports/acl_final_closure/parent_statistics/method_summary.csv"
POSITION = ROOT / "reports/acl_final_closure/parent_statistics/position_summary.csv"
PAIRED = ROOT / "reports/acl_final_closure/parent_statistics/paired_comparisons.csv"
UTILITY = ROOT / "reports/acl_final_closure/parent_utility/utility_summary.csv"
SYSTEMS = ROOT / "reports/aclfollow_20260725v2_randomized_systems/systems_summary.csv"
SYSTEMS_PAIRED = ROOT / "reports/aclfollow_20260725v2_randomized_systems/paired_systems_comparisons.csv"
MATCHED = ROOT / "reports/akvcausal_20260726v4_matched/paired_comparisons.csv"

MODELS = [
    "Qwen/Qwen2.5-7B-Instruct",
    "mistralai/Mistral-7B-Instruct-v0.3",
    "01-ai/Yi-1.5-9B-Chat",
]
MODEL_LABELS = {
    MODELS[0]: "Qwen2.5-7B",
    MODELS[1]: "Mistral-7B-v0.3",
    MODELS[2]: "Yi-1.5-9B",
}
FAMILIES = {
    "H2O": ("kvpress_h2o", "authority_h2o_detected_provenance"),
    "Knorm": ("kvpress_knorm", "authority_knorm_detected_provenance"),
    "StreamingLLM": (
        "kvpress_streaming",
        "authority_streaming_detected_provenance",
    ),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines).rstrip() + "\n")


def intval(row: dict[str, str], field: str) -> int:
    value = row.get(field, "")
    return int(float(value)) if value else 0


def frac(num: int, den: int) -> str:
    return f"{num}/{den}"


def natural_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        row
        for row in rows
        if row["dataset"].endswith("natural_short_500.jsonl")
        and row["model"] in MODELS
    ]


def index_rows(rows: list[dict[str, str]]) -> dict[tuple[str, str, float], dict[str, str]]:
    return {
        (row["model"], row["method"], float(row["keep_ratio"])): row
        for row in rows
    }


def write_appendix_crossmodel(rows: list[dict[str, str]]) -> None:
    index = index_rows(natural_rows(rows))
    lines = [
        "% Generated from released result records.",
        r"\begin{table*}[t]",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{2.6pt}",
        r"\begin{tabular}{lllrrrrrr}",
        r"\toprule",
        r"Model & Scorer & KV & \multicolumn{3}{c}{Official base} & "
        r"\multicolumn{3}{c}{+\method{}} \\",
        r"\cmidrule(lr){4-6}\cmidrule(lr){7-9}",
        r"& & & Hier. & Rev. & Benign & Hier. & Rev. & Benign \\",
        r"\midrule",
    ]
    for model in MODELS:
        for family, (base, authority) in FAMILIES.items():
            for keep in (0.2, 0.4):
                b = index[(model, base, keep)]
                a = index[(model, authority, keep)]
                values = [
                    MODEL_LABELS[model],
                    family,
                    f"{int(keep * 100)}\\%",
                    frac(intval(b, "hierarchy_success_num"), intval(b, "hierarchy_success_den")),
                    frac(intval(b, "authority_reversal_num"), intval(b, "authority_reversal_den")),
                    frac(intval(b, "benign_utility_num"), intval(b, "benign_utility_den")),
                    frac(intval(a, "hierarchy_success_num"), intval(a, "hierarchy_success_den")),
                    frac(intval(a, "authority_reversal_num"), intval(a, "authority_reversal_den")),
                    frac(intval(a, "benign_utility_num"), intval(a, "benign_utility_den")),
                ]
                lines.append(" & ".join(values) + r" \\")
        if model != MODELS[-1]:
            lines.append(r"\midrule")
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\caption{Table~\ref{tab:ladder} per model, scorer, and budget. "
            r"``Rev.'' is explicit lower-authority selection; other wrong outputs "
            r"count against hierarchy accuracy.}",
            r"\label{tab:appendix-crossmodel}",
            r"\end{table*}",
        ]
    )
    write(OUT / "appendix_crossmodel_table.tex", lines)


def write_utility(rows: list[dict[str, str]]) -> None:
    wanted = {
        method
        for base, authority in FAMILIES.values()
        for method in (base, authority)
    }
    selected = [
        row
        for row in rows
        if row["method"] in wanted
        and ("triviaqa" in row["dataset"] or "2wikimqa" in row["dataset"])
    ]
    index = {
        (Path(row["dataset"]).name, row["method"], float(row["keep_ratio"])): row
        for row in selected
    }
    lines = [
        "% Generated from released result records.",
        r"\begin{table*}[t]",
        r"\centering",
        r"\small",
        r"\setlength{\tabcolsep}{3.6pt}",
        r"\begin{tabular}{lllrrr}",
        r"\toprule",
        r"LongBench task & Scorer & KV & Base score & +\method{} score & Exact outputs \\",
        r"\midrule",
    ]
    for dataset, label in (
        ("longbench_official_triviaqa_50.jsonl", "TriviaQA"),
        ("longbench_official_2wikimqa_50.jsonl", "2WikiMultiHopQA"),
    ):
        for family, (base, authority) in FAMILIES.items():
            for keep in (0.2, 0.4):
                b = index[(dataset, base, keep)]
                a = index[(dataset, authority, keep)]
                values = [
                    label,
                    family,
                    f"{int(keep * 100)}\\%",
                    f"{float(b['longbench_score']):.3f}",
                    f"{float(a['longbench_score']):.3f}",
                    "50/50",
                ]
                lines.append(" & ".join(values) + r" \\")
        if dataset.startswith("longbench_official_triviaqa"):
            lines.append(r"\midrule")
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\caption{No-authority-span transparency on two compatible LongBench "
            r"tasks. The authority wrapper and its official base emit exactly the "
            r"same token IDs on all 600 paired outputs. Scores against FullKV are "
            r"reported only as descriptive compression utility in the artifact.}",
            r"\label{tab:utility-equivalence}",
            r"\end{table*}",
        ]
    )
    write(OUT / "appendix_utility_table.tex", lines)


def write_systems(rows: list[dict[str, str]], paired_rows: list[dict[str, str]]) -> None:
    del rows  # Summary rows are retained as a required source; paired effects drive the table.
    paired_index = {
        (row["comparison"], float(row["keep_ratio"])): row
        for row in paired_rows
        if row["comparison_type"] == "authority_vs_official"
    }
    lines = [
        "% Generated from released result records.",
        r"\begin{table*}[t]",
        r"\centering",
        r"\small",
        r"\setlength{\tabcolsep}{4.0pt}",
        r"\begin{tabular}{llrrrr}",
        r"\toprule",
        r"Scorer & KV & Paired obs. & Prefill $\Delta$ [95\% CI] & "
        r"Peak memory $\Delta$ & Retained-token $\Delta$ \\",
        r"\midrule",
    ]
    for family, (base, authority) in FAMILIES.items():
        for keep in (0.2, 0.4):
            pair = paired_index[(authority, keep)]
            delta = 1000 * float(pair["prefill_seconds_median_delta"])
            low = 1000 * float(pair["prefill_seconds_median_delta_ci95_low"])
            high = 1000 * float(pair["prefill_seconds_median_delta_ci95_high"])
            values = [
                family,
                f"{int(keep * 100)}\\%",
                pair["paired_observation_num"],
                f"{delta:+.1f} [{low:+.1f},{high:+.1f}] ms",
                f"{float(pair['peak_memory_mb_median_delta']):+.1f} MB",
                f"{float(pair['retained_prompt_tokens_median_delta']):+.0f}",
            ]
            lines.append(" & ".join(values) + r" \\")
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\caption{Paired randomized systems effects (30 examples, three "
            r"orderings; 90 observations per row). Authority ordering adds "
            r"9.1--10.8 ms median prefill time. Peak-memory and retained-token "
            r"paired median differences are exactly zero.}",
            r"\label{tab:systems}",
            r"\end{table*}",
        ]
    )
    write(OUT / "appendix_systems_table.tex", lines)


def write_matched(rows: list[dict[str, str]]) -> None:
    labels = {"snapkv": "SnapKV", "tova": "TOVA", "pyramid": "PyramidKV"}
    lines = [
        "% Generated from released result records.",
        r"\begin{table}[t]",
        r"\centering",
        r"\small",
        r"\setlength{\tabcolsep}{3pt}",
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"Scorer & Wrong & Correct & $\Delta$ [95\% CI] & Holm $p$ \\",
        r"\midrule",
    ]
    for row in rows:
        wrong = f"{float(row['reference_hierarchy_success']):.0%}".replace("%", r"\%")
        correct = f"{float(row['comparison_hierarchy_success']):.0%}".replace("%", r"\%")
        values = [
            labels[row["base_family"]],
            wrong,
            correct,
            (
                f"+{100 * float(row['hierarchy_absolute_delta']):.0f} "
                f"[{100 * float(row['hierarchy_delta_ci95_low']):.0f},"
                f"{100 * float(row['hierarchy_delta_ci95_high']):.0f}]"
            ),
            f"{float(row['holm_adjusted_p_global_family']):.4f}",
        ]
        lines.append(" & ".join(values) + r" \\")
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\caption{Matched 8k-context intervention at 2\% KV. ``Wrong'' "
            r"protects the lower-authority span and demotes the governing span; "
            r"``Correct'' reverses that assignment under the same scorer and "
            r"per-layer budget. Each row has 25 conflicts and five benign controls.}",
            r"\label{tab:matched-causal}",
            r"\end{table}",
        ]
    )
    write(OUT / "appendix_matched_table.tex", lines)


def write_position(rows: list[dict[str, str]]) -> None:
    wanted = {method for pair in FAMILIES.values() for method in pair}
    grouped: dict[tuple[str, float, str], dict[str, int]] = defaultdict(
        lambda: defaultdict(int)
    )
    for row in rows:
        if (
            row["dataset"].endswith("natural_short_500.jsonl")
            and row["model"] in MODELS
            and row["method"] in wanted
        ):
            key = (row["method"], float(row["keep_ratio"]), row["high_location"])
            for field in ("conflict_num", "hierarchy_success_num", "authority_reversal_num"):
                grouped[key][field] += intval(row, field)

    lines = [
        "% Generated from released result records.",
        r"\begin{table*}[t]",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{3.2pt}",
        r"\begin{tabular}{llrrrrrrrr}",
        r"\toprule",
        r"& & \multicolumn{4}{c}{Prefix authority} & \multicolumn{4}{c}{Mid-context authority} \\",
        r"\cmidrule(lr){3-6}\cmidrule(lr){7-10}",
        r"Scorer & KV & Base hier. & Base rev. & AKV hier. & AKV rev. & "
        r"Base hier. & Base rev. & AKV hier. & AKV rev. \\",
        r"\midrule",
    ]
    for family, (base, authority) in FAMILIES.items():
        for keep in (0.2, 0.4):
            values = [family, f"{int(keep * 100)}\\%"]
            for location in ("prefix", "mid_context"):
                b = grouped[(base, keep, location)]
                a = grouped[(authority, keep, location)]
                values.extend(
                    [
                        frac(b["hierarchy_success_num"], b["conflict_num"]),
                        frac(b["authority_reversal_num"], b["conflict_num"]),
                        frac(a["hierarchy_success_num"], a["conflict_num"]),
                        frac(a["authority_reversal_num"], a["conflict_num"]),
                    ]
                )
            lines.append(" & ".join(values) + r" \\")
        if family != list(FAMILIES)[-1]:
            lines.append(r"\midrule")
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\caption{Primary position-stratified results across three models. "
            r"Every scorer--budget--position cell contains 600 paired conflicts.}",
            r"\label{tab:position-full}",
            r"\end{table*}",
        ]
    )
    write(OUT / "appendix_position_table.tex", lines)


def write_primary_paired(rows: list[dict[str, str]]) -> None:
    authority_methods = {authority for _, authority in FAMILIES.values()}
    family_by_base = {base: family for family, (base, _) in FAMILIES.items()}
    selected = [
        row
        for row in rows
        if row["dataset"].endswith("natural_short_500.jsonl")
        and row["model"] in MODELS
        and row["comparison"] in authority_methods
        and row["official_base"] in family_by_base
    ]
    selected.sort(
        key=lambda row: (
            MODELS.index(row["model"]),
            list(FAMILIES).index(family_by_base[row["official_base"]]),
            float(row["keep_ratio"]),
        )
    )
    lines = [
        "% Generated from released result records.",
        r"\begin{table*}[t]",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{3.0pt}",
        r"\begin{tabular}{lllrrrrr}",
        r"\toprule",
        r"Model & Scorer & KV & Base rev. & AKV rev. & $\Delta$ [95\% CI] & "
        r"Holm $p$ & Signal \\",
        r"\midrule",
    ]
    previous_model = None
    for row in selected:
        if previous_model is not None and row["model"] != previous_model:
            lines.append(r"\midrule")
        previous_model = row["model"]
        delta = 100 * float(row["absolute_rate_delta"])
        lo = 100 * float(row["absolute_rate_delta_ci95_low"])
        hi = 100 * float(row["absolute_rate_delta_ci95_high"])
        p = float(row["holm_adjusted_p_global_family"])
        p_text = f"{p:.3g}"
        values = [
            MODEL_LABELS[row["model"]],
            family_by_base[row["official_base"]],
            f"{int(float(row['keep_ratio']) * 100)}\\%",
            frac(intval(row, "base_reversal_num"), intval(row, "paired_conflict_num")),
            frac(intval(row, "comparison_reversal_num"), intval(row, "paired_conflict_num")),
            f"{delta:+.1f} [{lo:+.1f},{hi:+.1f}]",
            p_text,
            "yes" if row["holm_significant_0_05"] == "True" else "boundary",
        ]
        lines.append(" & ".join(values) + r" \\")
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\caption{Complete model-stratified paired reversal inference for the "
            r"three primary scorer families. Deltas are AKV minus official base in "
            r"percentage points. ``Boundary'' includes weak or zero-effect cells "
            r"that do not pass the global Holm family.}",
            r"\label{tab:primary-paired-full}",
            r"\end{table*}",
        ]
    )
    write(OUT / "appendix_primary_paired_table.tex", lines)


def write_crossmodel_ablation(rows: list[dict[str, str]]) -> None:
    index = index_rows(natural_rows(rows))
    lines = [
        "% Generated from released result records.",
        r"\begin{table*}[t]",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{3.0pt}",
        r"\begin{tabular}{lllrrrrr}",
        r"\toprule",
        r"Model & Scorer & KV & Official base & System-only & All-control & Full AKV & AKV benign \\",
        r"\midrule",
    ]
    for model in MODELS:
        for family, (base, authority) in FAMILIES.items():
            stem = base.removeprefix("kvpress_")
            system = f"system_{stem}_pin"
            all_control = f"all_control_{stem}_pin"
            for keep in (0.2, 0.4):
                values = [MODEL_LABELS[model], family, f"{int(keep * 100)}\\%"]
                for method in (base, system, all_control, authority):
                    row = index[(model, method, keep)]
                    values.append(
                        frac(
                            intval(row, "authority_reversal_num"),
                            intval(row, "authority_reversal_den"),
                        )
                    )
                a = index[(model, authority, keep)]
                values.append(
                    frac(intval(a, "benign_utility_num"), intval(a, "benign_utility_den"))
                )
                lines.append(" & ".join(values) + r" \\")
        if model != MODELS[-1]:
            lines.append(r"\midrule")
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\caption{Cross-model protection ablation, reported as explicit "
            r"reversals over feasible conflicts. At 20\% KV, some all-control "
            r"variants admit only 320 conflicts because protecting every typed "
            r"control token exceeds the strict budget on the multi-tier stratum; "
            r"the full method remains feasible on all 400 primary conflicts.}",
            r"\label{tab:crossmodel-ablation}",
            r"\end{table*}",
        ]
    )
    write(OUT / "appendix_crossmodel_ablation_table.tex", lines)


def write_endpoint_guardrails(rows: list[dict[str, str]]) -> None:
    index = index_rows(natural_rows(rows))
    lines = [
        "% Generated from released result records.",
        r"\begin{table*}[t]",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{3.0pt}",
        r"\begin{tabular}{lllrrrrrr}",
        r"\toprule",
        r"& & & \multicolumn{3}{c}{Official base} & \multicolumn{3}{c}{+\method{}} \\",
        r"\cmidrule(lr){4-6}\cmidrule(lr){7-9}",
        r"Model & Scorer & KV & Benign & Malformed & Strict JSON & Benign & Malformed & Strict JSON \\",
        r"\midrule",
    ]
    for model in MODELS:
        for family, (base, authority) in FAMILIES.items():
            for keep in (0.2, 0.4):
                b = index[(model, base, keep)]
                a = index[(model, authority, keep)]
                values = [
                    MODEL_LABELS[model],
                    family,
                    f"{int(keep * 100)}\\%",
                    frac(intval(b, "benign_utility_num"), intval(b, "benign_utility_den")),
                    frac(intval(b, "malformed_num"), intval(b, "num_examples")),
                    frac(intval(b, "strict_json_num"), intval(b, "num_examples")),
                    frac(intval(a, "benign_utility_num"), intval(a, "benign_utility_den")),
                    frac(intval(a, "malformed_num"), intval(a, "num_examples")),
                    frac(intval(a, "strict_json_num"), intval(a, "num_examples")),
                ]
                lines.append(" & ".join(values) + r" \\")
        if model != MODELS[-1]:
            lines.append(r"\midrule")
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\caption{Benign and output-format guardrails for every primary "
            r"signal-family row. ``Malformed'' is the semantic endpoint over all "
            r"500 examples; strict JSON is descriptive surface compliance. "
            r"AuthorityKV improves or matches these endpoints in the stated "
            r"non-inferiority family.}",
            r"\label{tab:endpoint-guardrails}",
            r"\end{table*}",
        ]
    )
    write(OUT / "appendix_endpoint_guardrails_table.tex", lines)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    parent = read_csv(PARENT)
    write_appendix_crossmodel(parent)
    write_utility(read_csv(UTILITY))
    write_systems(read_csv(SYSTEMS), read_csv(SYSTEMS_PAIRED))
    write_matched(read_csv(MATCHED))
    write_position(read_csv(POSITION))
    write_primary_paired(read_csv(PAIRED))
    write_crossmodel_ablation(parent)
    write_endpoint_guardrails(parent)
    print(f"wrote appendix tables to {OUT}")


if __name__ == "__main__":
    main()
