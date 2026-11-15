#!/usr/bin/env python3
"""Score a finished mixed-evidence or System-IFEval run with the frozen scorers (subprocess, outputs inside the run dir).
Inputs to the scorer: the stored FullKV predictions (gate) + this run's predictions (+ the stored base/AKV run when
no method@ratio collides). Writes <run>/scored_metrics.json and <run>/scored_judgments.jsonl and records the
scorer sha256 + inputs in <run>/scored_inputs.json.
Usage: python review_experiments/score_run.py <run_dir> [<run_dir> ...]"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import akv_common as C  # noqa: E402

RES = C.REPO / "results" / "authoritykv"
FULLKV = {"mixed": RES / "arrmixed_20260726v1_qwen_fullkv_full300" / "predictions.jsonl", "sys": RES / "arrsys_20260726v2_qwen_fullkv_full150" / "predictions.jsonl"}
STORED = {("mixed", "streaming"): RES / "arrmixed_20260726v4_qwen_streaming_full300" / "predictions.jsonl",
          ("mixed", "knorm"): RES / "arrmixed_20260726v4_qwen_knorm40_full300" / "predictions.jsonl",
          ("sys", "streaming"): RES / "arrsys_20260726v4_qwen_streaming40_full150" / "predictions.jsonl",
          ("sys", "knorm"): RES / "arrsys_20260726v4_qwen_knorm40_full150" / "predictions.jsonl"}
SCORER = {"mixed": "scripts/score_mixed_evidence_attack.py", "sys": "scripts/score_system_ifeval.py"}


def cells(path: Path) -> set[tuple[str, str, float]]:
    return {(str(r["example_id"]), str(r["method"]), round(float(r["keep_ratio"]), 4)) for r in C.read_jsonl(path)}


def score(run: Path) -> dict:
    summ = json.load((run / "summary.json").open())
    task = summ["task"]
    if task not in SCORER:
        return {"skipped": task}
    model_tag = summ.get("model_tag", "qwen7b")
    inputs = [FULLKV[task], run / "predictions.jsonl"]
    stored = STORED.get((task, summ["scorer"]))
    if stored is not None and model_tag == "qwen7b":
        mine = cells(run / "predictions.jsonl")
        if not (mine & cells(stored)):
            inputs.append(stored)
    if model_tag != "qwen7b":
        # other models: their own FullKV rows must come from the run itself (X1b pilot / X1c / X2 gates carry method 'fullkv') or from a
        # sibling FullKV run of the SAME task (fixed 2026-09-18T07:05Z: the old glob picked the first *fullkv* run of the model
        # regardless of task, e.g. the X1a IH-Challenge run for the X1b System-IFEval pilot → "unknown example ids").
        own = any(str(r.get("method")) == "fullkv" for r in C.read_jsonl(run / "predictions.jsonl"))
        if own:
            inputs = [run / "predictions.jsonl"]
        else:
            fk = []
            for d in sorted(C.RUNS_DIR.glob(f"*_X*fullkv*_{model_tag}_*")):
                sj = d / "summary.json"
                if sj.exists() and (d / "predictions.jsonl").exists() and json.load(sj.open()).get("task") == task:
                    fk.append(d)
            # several same-task FullKV siblings (e.g. X1b pilot30 and the full 150): take the one with the most fullkv rows
            fk.sort(key=lambda d: -sum(1 for r in C.read_jsonl(d / "predictions.jsonl") if str(r.get("method")) == "fullkv"))
            inputs[0] = next((d / "predictions.jsonl" for d in fk), inputs[0])
    out = run / "scored_metrics.json"
    jud = run / "scored_judgments.jsonl"
    cmd = [sys.executable, str(C.REPO / SCORER[task]), "--predictions", *map(str, inputs), "--out", str(out), "--judgments-out", str(jud)]
    proc = subprocess.run(cmd, cwd=str(C.REPO), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    rec = {"task": task, "inputs": [str(p) for p in inputs], "scorer": SCORER[task], "scorer_sha256": C.sha256_file(C.REPO / SCORER[task]), "exit": proc.returncode, "tail": proc.stdout[-1500:], "scored_at": C.now_iso()}
    C.write_json(run / "scored_inputs.json", rec)
    return rec


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        r = score(Path(arg).resolve())
        print(arg, r.get("exit", r))
