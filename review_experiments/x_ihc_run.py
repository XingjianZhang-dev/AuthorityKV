#!/usr/bin/env python3
"""X1a (PREREG-14): thin wrapper around the frozen IH-Challenge runner scripts/run_kvpress_ih_challenge.py
(subprocess; --out-dir redirected into the run dir) + config.json / summary.json / validation."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import akv_common as C  # noqa: E402

DATASET = "data/external_safety/ih_challenge_blue_team_auto_quoted_system_40.jsonl"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--model-tag", required=True)
    p.add_argument("--methods", required=True)
    p.add_argument("--keep-ratios", default="0.2,0.4")
    p.add_argument("--out-dir", required=True)
    args = p.parse_args()
    out = Path(args.out_dir).resolve(); out.mkdir(parents=True, exist_ok=True)
    runner = C.REPO / "scripts" / "run_kvpress_ih_challenge.py"
    cfg = C.base_config(experiment_id="X1a", runner_version="current", model=args.model, dtype="bf16", seed=20260530, keep_ratio=None, variant=args.methods,
                        hyperparams={"frozen_runner": "scripts/run_kvpress_ih_challenge.py", "frozen_runner_sha256": C.sha256_file(runner), "dataset": DATASET, "dataset_sha256": C.sha256_file(C.REPO / DATASET),
                                     "max_new_tokens": 16, "keep_ratios": args.keep_ratios, "grader": "record-level grader_code_python (preserved)"}, extra={"prereg_id": "PREREG-14"})
    C.write_json(out / "config.json", cfg)
    cmd = [sys.executable, str(runner), "--run-id", out.name, "--model", args.model, "--dataset", DATASET, "--methods", args.methods, "--keep-ratios", args.keep_ratios,
           "--max-new-tokens", "16", "--dtype", "bf16", "--experiment-config", "configs/acl_main_followup_matrix.json", "--out-dir", str(out)]
    print(" ".join(cmd), flush=True)
    rc = subprocess.call(cmd, cwd=str(C.REPO))
    rows = C.read_jsonl(out / "predictions.jsonl") if (out / "predictions.jsonl").exists() else []
    metrics = json.load((out / "metrics.json").open()) if (out / "metrics.json").exists() else {}
    ids = [str(r["example_id"]) for r in rows]
    n_methods = len({(r["method"], r["keep_ratio"]) for r in rows})
    val = {"exit": rc, "rows": len(rows), "row_count_ok": len(rows) == 40 * n_methods, "runtime_errors": sum(1 for r in rows if r.get("status") == "runtime_error"),
           "empty_outputs": sum(1 for r in rows if r.get("status") == "ok" and not str(r.get("output_text", "")).strip())}
    rc_cfg = json.load((out / "run_config.json").open()) if (out / "run_config.json").exists() else {}
    cfg["model_revision"] = rc_cfg.get("model_commit")
    summary = {"experiment": "X1a", "task": "ihc", "model_tag": args.model_tag, "model": args.model, "methods": args.methods, "metrics_by_method": metrics.get("by_method", {}),
               "validation": val, "valid": rc == 0 and val["row_count_ok"] and val["runtime_errors"] == 0}
    C.write_json(out / "summary.json", summary)
    peak = [r.get("peak_memory_mb") or 0 for r in rows]
    C.write_json(out / "peak_mem.json", {"max_example_peak_memory_mb": max(peak) if peak else None})
    cfg["end_time"] = C.now_iso(); C.write_json(out / "config.json", cfg)
    print(json.dumps({"DONE": str(out), "valid": summary["valid"], "by_method": {k: {kk: v.get(kk) for kk in ("official_accuracy_num", "official_accuracy_den", "injection_follow_num", "strict_city_format_num")} for k, v in metrics.get("by_method", {}).items()}}, indent=1))
    sys.exit(0 if rc == 0 else rc)


if __name__ == "__main__":
    main()
