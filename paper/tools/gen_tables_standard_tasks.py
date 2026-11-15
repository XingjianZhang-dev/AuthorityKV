#!/usr/bin/env python3
"""Appendix tables of the standard tasks (System-IFEval and LongBench with an injected instruction).

Reads the stored scorer outputs under reports/ and the run records under results/authoritykv/ (extract
raw_outputs/ first) and writes the LaTeX tables under paper/generated/.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
GENERATED = ROOT / "paper" / "generated"

STREAMING = (
    ROOT
    / "reports/arr_august_external_closure/full/"
    "mixed_evidence_streaming_full_v4_metrics.json"
)
KNORM = (
    ROOT
    / "reports/arr_august_external_closure/full/"
    "mixed_evidence_knorm40_full_v4_metrics.json"
)
IFEVAL = (
    ROOT
    / "reports/arr_august_external_closure/full/"
    "system_ifeval_full_v4_metrics.json"
)
CROSSMODEL_GATE = (
    ROOT
    / "reports/arr_august_external_closure/upgrade/"
    "crossmodel_gate_decision.json"
)
CROSSMODEL_GATE_AUDIT = (
    ROOT
    / "reports/arr_august_external_closure/upgrade/"
    "crossmodel_fullkv_pilot_execution_audit.json"
)


def read_json(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        return json.load(handle)


def write_text(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n")


def mixed_rows() -> list[dict[str, Any]]:
    sources = {"Streaming": read_json(STREAMING), "Knorm": read_json(KNORM)}
    specs = [
        (
            "Streaming",
            0.2,
            "kvpress_streaming",
            "authority_streaming_detected_provenance",
        ),
        (
            "Streaming",
            0.4,
            "kvpress_streaming",
            "authority_streaming_detected_provenance",
        ),
        (
            "Knorm",
            0.4,
            "kvpress_knorm",
            "authority_knorm_detected_provenance",
        ),
    ]
    output: list[dict[str, Any]] = []
    for label, keep, base_name, authority_name in specs:
        data = sources[label]
        condition = "explicit_attack"
        base_key = f"{base_name}@{keep:.2f}/{condition}"
        authority_key = f"{authority_name}@{keep:.2f}/{condition}"
        pair_key = f"{base_name}_vs_{authority_name}@{keep:.2f}/{condition}"
        base = data["by_method_condition"][base_key]["fullkv_capable_rows"]
        authority = data["by_method_condition"][authority_key][
            "fullkv_capable_rows"
        ]
        paired = data["paired_comparisons"][pair_key]["fullkv_capable_rows"]
        output.append(
            {
                "panel": "mixed_evidence",
                "scorer": label,
                "keep_ratio": keep,
                "gate_num": data["fullkv_capability_gate"]["capable_pairs"],
                "gate_den": data["fullkv_capability_gate"]["all_pairs"],
                "base_attack_num": base["attack_success_num"],
                "base_attack_den": base["attack_success_den"],
                "base_attack_rate": base["attack_success_rate"],
                "authority_attack_num": authority["attack_success_num"],
                "authority_attack_den": authority["attack_success_den"],
                "authority_attack_rate": authority["attack_success_rate"],
                "attack_delta": paired["attack_success_rate"][
                    "authority_minus_base"
                ],
                "attack_ci_low": paired["attack_success_rate"][
                    "paired_bootstrap95"
                ][0],
                "attack_ci_high": paired["attack_success_rate"][
                    "paired_bootstrap95"
                ][1],
                "base_longbench": base["longbench_score"],
                "authority_longbench": authority["longbench_score"],
                "longbench_delta": paired["longbench_score"][
                    "authority_minus_base"
                ],
                "longbench_ci_low": paired["longbench_score"][
                    "paired_bootstrap95"
                ][0],
                "longbench_ci_high": paired["longbench_score"][
                    "paired_bootstrap95"
                ][1],
                "base_joint_num": base["safe_utility_joint_num"],
                "base_joint_den": base["safe_utility_joint_den"],
                "authority_joint_num": authority["safe_utility_joint_num"],
                "authority_joint_den": authority["safe_utility_joint_den"],
                "joint_delta": paired["safe_utility_joint"][
                    "authority_minus_base"
                ],
                "joint_ci_low": paired["safe_utility_joint"][
                    "paired_bootstrap95"
                ][0],
                "joint_ci_high": paired["safe_utility_joint"][
                    "paired_bootstrap95"
                ][1],
                "joint_mcnemar_p": paired["safe_utility_joint"][
                    "mcnemar_exact_two_sided_p"
                ],
            }
        )
    return output


def make_appendix_ifeval_table() -> None:
    data = read_json(IFEVAL)
    methods = [
        ("FullKV", "fullkv@1.00"),
        ("Streaming", "kvpress_streaming@0.40"),
        ("Streaming+AKV", "authority_streaming_detected_provenance@0.40"),
        ("Knorm", "kvpress_knorm@0.40"),
        ("Knorm+AKV", "authority_knorm_detected_provenance@0.40"),
    ]
    lines = [
        "% Generated from released result records.",
        r"\begin{table*}[t]",
        r"\centering",
        r"\small",
        r"\setlength{\tabcolsep}{4.2pt}",
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"& \multicolumn{2}{c}{All 150 prompts} & "
        r"\multicolumn{2}{c}{88 FullKV-strict prompts} \\",
        r"\cmidrule(lr){2-3}\cmidrule(lr){4-5}",
        r"Method & Prompt strict & Instruction strict & Prompt strict & Instruction strict \\",
        r"\midrule",
    ]
    for label, key in methods:
        all_rows = data["by_method"][key]["all_prompts"]
        gated = data["by_method"][key]["fullkv_strict_correct_prompts"]
        lines.append(
            " & ".join(
                [
                    label,
                    f"{all_rows['prompt_strict_num']}/{all_rows['prompt_strict_den']}",
                    f"{all_rows['instruction_strict_num']}/{all_rows['instruction_strict_den']}",
                    f"{gated['prompt_strict_num']}/{gated['prompt_strict_den']}",
                    f"{gated['instruction_strict_num']}/{gated['instruction_strict_den']}",
                ]
            )
            + r" \\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\caption{Complete System-IFEval strict results under the official "
            r"grader (\(\mathrm{R}_{\uparrow}\) rule). The capability-gated columns isolate compression-induced "
            r"changes; all-prompt columns preserve the unconditional denominator.}",
            r"\label{tab:ifeval-full}",
            r"\end{table*}",
        ]
    )
    write_text(GENERATED / "appendix_ifeval_table.tex", lines)


def make_appendix_crossmodel_gate_rows() -> None:
    decision = read_json(CROSSMODEL_GATE)
    rows = {row["label"]: row for row in decision["rows"]}
    expected = {
        "mistral7b": ("Mistral", 14),
        "yi9b": ("Yi", 7),
    }
    if (
        decision.get("status") != "STOP"
        or decision.get("selected_model_label") is not None
        or set(rows) != set(expected)
    ):
        raise RuntimeError("cross-model external gate is not the audited STOP boundary")
    lines = ["% Generated from released result records."]
    for label, (display, correct) in expected.items():
        row = rows[label]
        if (
            row["correct"] != correct
            or row["total"] != 30
            or row["eligible"]
        ):
            raise RuntimeError(f"unexpected cross-model gate row: {row}")
        lines.extend(
            [
                f"System-IFEval {display} pilot & {correct}/30 prompt-strict; gate is 15/30 &",
                r"Stopped by gate & Compression result intentionally not estimated. \\",
            ]
        )
    write_text(GENERATED / "appendix_crossmodel_external_gate_rows.tex", lines)


def make_appendix_mixed_table() -> None:
    rows = mixed_rows()
    lines = [
        "% Generated from released result records.",
        r"\begin{table*}[t]",
        r"\centering",
        r"\small",
        r"\setlength{\tabcolsep}{3.0pt}",
        r"\begin{tabular}{llrrrrrr}",
        r"\toprule",
        r"Scorer & KV & \multicolumn{2}{c}{Attack success} & "
        r"\multicolumn{2}{c}{Safe + useful} & \multicolumn{2}{c}{LongBench score} \\",
        r"\cmidrule(lr){3-4}\cmidrule(lr){5-6}\cmidrule(lr){7-8}",
        r"& & Base & +AKV & Base & +AKV & Base & +AKV \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            " & ".join(
                [
                    row["scorer"],
                    f"{int(100 * row['keep_ratio'])}\\%",
                    f"{row['base_attack_num']}/64",
                    rf"\textbf{{{row['authority_attack_num']}/64}}",
                    f"{row['base_joint_num']}/64",
                    rf"\textbf{{{row['authority_joint_num']}/64}}",
                    f"{row['base_longbench']:.3f}",
                    rf"\textbf{{{row['authority_longbench']:.3f}}}",
                ]
            )
            + r" \\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\caption{Mixed useful-evidence plus explicit-attack results on all "
            r"64 FullKV-capable source pairs. Counts and scores use the \(\mathrm{R}_{\uparrow}\) rule "
            r"(both rules: Table~\ref{tab:app-mixed}); attack headroom exists only for "
            r"StreamingLLM. The unconditional 100-pair results and clean/paraphrase "
            r"conditions are retained in the artifact.}",
            r"\label{tab:mixed-full}",
            r"\end{table*}",
        ]
    )
    write_text(GENERATED / "appendix_mixed_table.tex", lines)


def make_appendix_mixed_conditions_table() -> None:
    sources = {"Streaming": read_json(STREAMING), "Knorm": read_json(KNORM)}
    specs = [
        (
            "Streaming",
            0.2,
            "kvpress_streaming",
            "authority_streaming_detected_provenance",
        ),
        (
            "Streaming",
            0.4,
            "kvpress_streaming",
            "authority_streaming_detected_provenance",
        ),
        (
            "Knorm",
            0.4,
            "kvpress_knorm",
            "authority_knorm_detected_provenance",
        ),
    ]
    conditions = [
        ("clean", "Clean"),
        ("explicit_attack", "Explicit"),
        ("paraphrase_attack", "Paraphrase"),
    ]
    populations = [
        ("all_rows", "All", 100),
        ("fullkv_capable_rows", "Gated", 64),
    ]
    lines = [
        "% Generated from released result records.",
        r"\begin{table*}[t]",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{2.4pt}",
        r"\begin{tabular}{lllrrrr}",
        r"\toprule",
        r"Scorer / KV & Condition & Population & Attack (base$\rightarrow$AKV) & "
        r"Joint (base$\rightarrow$AKV) & LB (base$\rightarrow$AKV) & "
        r"Paired $\Delta$LB [95\% CI] \\",
        r"\midrule",
    ]
    for label, keep, base_name, authority_name in specs:
        data = sources[label]
        for condition, condition_label in conditions:
            base_key = f"{base_name}@{keep:.2f}/{condition}"
            authority_key = f"{authority_name}@{keep:.2f}/{condition}"
            pair_key = f"{base_name}_vs_{authority_name}@{keep:.2f}/{condition}"
            for population, population_label, expected_n in populations:
                base = data["by_method_condition"][base_key][population]
                authority = data["by_method_condition"][authority_key][population]
                paired = data["paired_comparisons"][pair_key][population]
                if base["rows"] != expected_n or authority["rows"] != expected_n:
                    raise RuntimeError(
                        f"unexpected mixed-evidence denominator for {pair_key}"
                    )
                low, high = paired["longbench_score"]["paired_bootstrap95"]
                lines.append(
                    " & ".join(
                        [
                            f"{label} / {int(100 * keep)}\\%",
                            condition_label,
                            f"{population_label} ({expected_n})",
                            (
                                f"{base['attack_success_num']}/{expected_n}"
                                rf"$\rightarrow${authority['attack_success_num']}/{expected_n}"
                            ),
                            (
                                f"{base['safe_utility_joint_num']}/{expected_n}"
                                rf"$\rightarrow${authority['safe_utility_joint_num']}/{expected_n}"
                            ),
                            (
                                f"{base['longbench_score']:.3f}"
                                rf"$\rightarrow${authority['longbench_score']:.3f}"
                            ),
                            (
                                f"{paired['longbench_score']['authority_minus_base']:+.3f} "
                                f"[{low:+.3f},{high:+.3f}]"
                            ),
                        ]
                    )
                    + r" \\"
                )
        if label != specs[-1][0] or keep != specs[-1][1]:
            lines.append(r"\addlinespace[1pt]")
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\caption{Complete mixed-evidence matrix (\(\mathrm{R}_{\uparrow}\) rule). ``All'' preserves the "
            r"unconditional 100-pair denominator; ``Gated'' contains the 64 source "
            r"pairs correct and attack-free under FullKV in all three conditions. "
            r"Attack markers and answer labels are used only after generation.}",
            r"\label{tab:mixed-all-conditions}",
            r"\end{table*}",
        ]
    )
    write_text(
        GENERATED / "appendix_mixed_conditions_table.tex",
        lines,
    )


def verify_sources() -> None:
    required = [STREAMING, KNORM, IFEVAL, CROSSMODEL_GATE, CROSSMODEL_GATE_AUDIT]
    missing = [path for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"missing result sources: {missing}")
    if read_json(CROSSMODEL_GATE_AUDIT).get("status") != "PASS":
        raise RuntimeError("cross-model FullKV pilot execution audit is not PASS")


def main() -> None:
    verify_sources()
    make_appendix_ifeval_table()
    make_appendix_crossmodel_gate_rows()
    make_appendix_mixed_table()
    make_appendix_mixed_conditions_table()
    print(f"wrote appendix tables to {GENERATED}")


if __name__ == "__main__":
    main()
