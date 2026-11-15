#!/usr/bin/env python3
"""Scorer reproduction check (CPU only):
  * Table 6  <- scripts/score_system_ifeval.py (overlay version, sha 42480b30) on the stored System-IFEval predictions
  * Table 8  <- scripts/score_mixed_evidence_attack.py on the stored mixed-evidence predictions
The frozen scorers are invoked unchanged as subprocesses with --out/--judgments-out redirected into runs/.
The new metrics are compared cell by cell with (i) the stored metrics files and (ii) the values reported in the paper.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import akv_common as C  # noqa: E402

PY = sys.executable
RES = C.REPO / "results" / "authoritykv"
REP = C.REPO / "reports" / "arr_august_external_closure" / "full"

# Paper Table 6 (prompt-strict): gated 88 / all 150
T6_PAPER = {
    "fullkv@1.00": {"all": 88},
    "kvpress_streaming@0.40": {"gated": 8, "all": 11},
    "authority_streaming_detected_provenance@0.40": {"gated": 48, "all": 61},
    "kvpress_knorm@0.40": {"gated": 24, "all": 28},
    "authority_knorm_detected_provenance@0.40": {"gated": 56, "all": 71},
}
# Paper Table 8 rows listed in EXPERIMENTS §5 (gated 64 pairs): (attack, joint, LB) base -> AKV
T8_PAPER = {
    ("streaming", 0.20, "explicit_attack"): {"base": (7, 54, 0.734), "akv": (0, 57, 0.828)},
    ("streaming", 0.40, "explicit_attack"): {"base": (6, 54, 0.767), "akv": (0, 59, 0.821)},
    ("streaming", 0.40, "paraphrase_attack"): {"base": (0, 61, 0.690), "akv": (0, 59, 0.847)},
    ("knorm", 0.40, "explicit_attack"): {"base": (0, 43, 0.410), "akv": (0, 48, 0.518)},
}


def run_scorer(script: str, predictions: list[Path], out_dir: Path, tag: str) -> Path:
    out = out_dir / f"{tag}_metrics.json"
    jud = out_dir / f"{tag}_judgments.jsonl"
    cmd = [PY, str(C.REPO / "scripts" / script), "--predictions", *map(str, predictions), "--out", str(out), "--judgments-out", str(jud)]
    with (out_dir / "log.txt").open("a") as log:
        log.write(f"[{C.now_iso()}] $ {' '.join(cmd)}\n")
        log.flush()
        proc = subprocess.run(cmd, cwd=str(C.REPO), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        log.write(proc.stdout[-4000:] + f"\n[{C.now_iso()}] exit={proc.returncode}\n")
    if proc.returncode != 0:
        raise SystemExit(f"{script} failed: {proc.stdout[-2000:]}")
    return out


def deep_diff(a, b, path="", out=None):
    out = [] if out is None else out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append((path + "/" + str(k), "missing", k in a, k in b))
            else:
                deep_diff(a[k], b[k], path + "/" + str(k), out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append((path, "len", len(a), len(b)))
        for i, (x, y) in enumerate(zip(a, b)):
            deep_diff(x, y, f"{path}[{i}]", out)
    else:
        if isinstance(a, float) and isinstance(b, float):
            if abs(a - b) > 1e-12:
                out.append((path, "value", a, b))
        elif a != b:
            out.append((path, "value", a, b))
    return out


def main() -> None:
    out_dir = C.new_run_dir("OVL-T6T8", "qwen7b", "streaming-knorm", "20-40")
    cfg = C.base_config(
        experiment_id="OVL-T6T8",
        runner_version="current",
        model="Qwen/Qwen2.5-7B-Instruct",
        dtype="n/a (CPU re-scoring of stored predictions)",
        seed=0,
        keep_ratio=None,
        variant="overlay_scorer_reproduction",
        hyperparams={
            "scorers": {
                "scripts/score_system_ifeval.py": C.sha256_file(C.REPO / "scripts/score_system_ifeval.py"),
                "scripts/score_mixed_evidence_attack.py": C.sha256_file(C.REPO / "scripts/score_mixed_evidence_attack.py"),
            },
            "grader_seeds": "python random.seed(0); langdetect DetectorFactory.seed=0 (inside score_system_ifeval.py)",
            "NLTK_DATA": os.environ.get("NLTK_DATA"),
        },
    )
    C.write_json(out_dir / "config.json", cfg)

    # --- Table 6 ---
    t6_inputs = [
        RES / "arrsys_20260726v2_qwen_fullkv_full150" / "predictions.jsonl",
        RES / "arrsys_20260726v4_qwen_streaming40_full150" / "predictions.jsonl",
        RES / "arrsys_20260726v4_qwen_knorm40_full150" / "predictions.jsonl",
    ]
    t6_new_path = run_scorer("score_system_ifeval.py", t6_inputs, out_dir, "system_ifeval_full")
    t6_new = json.load(t6_new_path.open())
    t6_old = json.load((REP / "system_ifeval_full_v4_metrics.json").open())
    t6_cells = {}
    for key, ref in T6_PAPER.items():
        new = t6_new["by_method"][key]
        old = t6_old["by_method"][key]
        n_all = new["all_prompts"]["prompt_strict_num"] if "prompt_strict_num" in new["all_prompts"] else None
        t6_cells[key] = {"new": new, "old": old, "paper": ref}
    t6_diff = deep_diff(t6_old["by_method"], t6_new["by_method"]) + deep_diff(
        t6_old["paired_comparisons"], t6_new["paired_comparisons"], "/paired"
    )

    # --- Table 8 ---
    t8_inputs_stream = [
        RES / "arrmixed_20260726v1_qwen_fullkv_full300" / "predictions.jsonl",
        RES / "arrmixed_20260726v4_qwen_streaming_full300" / "predictions.jsonl",
    ]
    t8_inputs_knorm = [
        RES / "arrmixed_20260726v1_qwen_fullkv_full300" / "predictions.jsonl",
        RES / "arrmixed_20260726v4_qwen_knorm40_full300" / "predictions.jsonl",
    ]
    t8s_new = json.load(run_scorer("score_mixed_evidence_attack.py", t8_inputs_stream, out_dir, "mixed_evidence_streaming_full").open())
    t8k_new = json.load(run_scorer("score_mixed_evidence_attack.py", t8_inputs_knorm, out_dir, "mixed_evidence_knorm40_full").open())
    t8s_old = json.load((REP / "mixed_evidence_streaming_full_v4_metrics.json").open())
    t8k_old = json.load((REP / "mixed_evidence_knorm40_full_v4_metrics.json").open())
    t8_diff = deep_diff(t8s_old["by_method_condition"], t8s_new["by_method_condition"], "/streaming") + deep_diff(
        t8k_old["by_method_condition"], t8k_new["by_method_condition"], "/knorm"
    ) + deep_diff(t8s_old["paired_comparisons"], t8s_new["paired_comparisons"], "/streaming_paired") + deep_diff(
        t8k_old["paired_comparisons"], t8k_new["paired_comparisons"], "/knorm_paired"
    )

    summary = {
        "table6": {"cells": {}, "new_vs_stored_overlay_diffs": t6_diff[:50], "n_diffs": len(t6_diff)},
        "table8": {"cells": {}, "new_vs_stored_overlay_diffs": t8_diff[:50], "n_diffs": len(t8_diff)},
        "stored_overlay_sha256": {
            "system_ifeval_full_v4_metrics.json": C.sha256_file(REP / "system_ifeval_full_v4_metrics.json"),
            "mixed_evidence_streaming_full_v4_metrics.json": C.sha256_file(REP / "mixed_evidence_streaming_full_v4_metrics.json"),
            "mixed_evidence_knorm40_full_v4_metrics.json": C.sha256_file(REP / "mixed_evidence_knorm40_full_v4_metrics.json"),
        },
        "inputs": {
            "table6": [str(p.relative_to(C.REPO)) for p in t6_inputs],
            "table8_streaming": [str(p.relative_to(C.REPO)) for p in t8_inputs_stream],
            "table8_knorm": [str(p.relative_to(C.REPO)) for p in t8_inputs_knorm],
        },
    }
    all_ok = True
    for key, ref in T6_PAPER.items():
        new = t6_new["by_method"][key]
        cell = {}
        for pop, sub in (("all", "all_prompts"), ("gated", "fullkv_strict_correct_prompts")):
            if pop in ref:
                got = new[sub]["prompt_strict_num"]
                den = new[sub]["prompt_strict_den"]
                cell[pop] = {"new": f"{got}/{den}", "paper": ref[pop], "equal": got == ref[pop]}
                all_ok &= got == ref[pop]
        summary["table6"]["cells"][key] = cell
    for (family, ratio, cond), ref in T8_PAPER.items():
        src = t8s_new if family == "streaming" else t8k_new
        for arm, method in (("base", f"kvpress_{family}"), ("akv", f"authority_{family}_detected_provenance")):
            g = src["by_method_condition"][f"{method}@{ratio:.2f}/{cond}"]["fullkv_capable_rows"]
            got = (g["attack_success_num"], g["safe_utility_joint_num"], round(g["longbench_score"], 3))
            eq = got[0] == ref[arm][0] and got[1] == ref[arm][1] and abs(got[2] - ref[arm][2]) < 0.0005
            all_ok &= eq
            summary["table8"]["cells"][f"{family}@{ratio:.2f}/{cond}/{arm}"] = {
                "new": {"attack": f"{got[0]}/{g['attack_success_den']}", "joint": f"{got[1]}/{g['safe_utility_joint_den']}", "LB": got[2]},
                "paper": {"attack": ref[arm][0], "joint": ref[arm][1], "LB": ref[arm][2]},
                "equal": eq,
            }
    summary["all_paper_cells_equal"] = all_ok
    summary["new_equals_stored_overlay"] = (len(t6_diff) == 0) and (len(t8_diff) == 0)
    C.write_json(out_dir / "summary.json", summary)
    C.write_json(out_dir / "peak_mem.json", {"note": "CPU-only re-scoring; no GPU memory used"})
    cfg["end_time"] = C.now_iso()
    C.write_json(out_dir / "config.json", cfg)
    print(json.dumps({"run_dir": str(out_dir), "all_paper_cells_equal": all_ok, "new_equals_stored_overlay": summary["new_equals_stored_overlay"], "t6_diffs": len(t6_diff), "t8_diffs": len(t8_diff)}, indent=1))
    for k, v in summary["table6"]["cells"].items():
        print("T6", k, v)
    for k, v in summary["table8"]["cells"].items():
        print("T8", k, v)


if __name__ == "__main__":
    main()
