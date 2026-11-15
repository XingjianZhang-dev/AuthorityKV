#!/usr/bin/env python3
"""X6 (PREREG-21): thin wrapper around the frozen external-utility / AgentDojo runners for Qwen2.5-14B
(subprocess; --out-dir redirected into the run dir) + config.json / summary.json / peak_mem.json.
  --bench ruler     → scripts/run_kvpress_external_utility.py on data/external_utility/ruler_official_qwen25_4k_24.jsonl
                      (same flags as the stored 7B gate run aclmain_20260725v1_qwen7b_utility_ruler4k_fullkv)
  --bench agentdojo → scripts/run_agentdojo_official_kv.py, workspace suite, injecagent, 10 pairs
                      (same flags as the stored 7B gate run aclfollow_20260725v2_qwen7b_agentdojo_fullkv10)
Gate decisions (RULER ≥ 18/24 FullKV, AgentDojo utility_and_safe ≥ 8/10) are made by build_x.py from metrics.json."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import akv_common as C  # noqa: E402

RULER = "data/external_utility/ruler_official_qwen25_4k_24.jsonl"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--bench", choices=["ruler", "agentdojo"], required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--model-tag", required=True)
    p.add_argument("--methods", required=True)
    p.add_argument("--keep-ratios", default="0.2,0.4")
    p.add_argument("--fullkv-run", default=None, help="AgentDojo compressed cells: the FullKV gate run dir (frozen runner --fullkv-run)")
    p.add_argument("--limit", type=int, default=None, help="dry run only: RULER --limit / AgentDojo --limit-pairs")
    p.add_argument("--out-dir", required=True)
    args = p.parse_args()
    out = Path(args.out_dir).resolve(); out.mkdir(parents=True, exist_ok=True)
    if args.bench == "ruler":
        runner = C.REPO / "scripts" / "run_kvpress_external_utility.py"
        cmd = [sys.executable, str(runner), "--run-id", out.name, "--model", args.model, "--dataset", RULER, "--methods", args.methods, "--keep-ratios", args.keep_ratios,
               "--max-new-tokens", "32", "--dtype", "bf16", "--use-chat-template", "--experiment-config", "configs/acl_main_followup_matrix.json", "--out-dir", str(out)]
        if args.limit:
            cmd += ["--limit", str(args.limit)]
        hyper = {"frozen_runner": "scripts/run_kvpress_external_utility.py", "dataset": RULER, "dataset_sha256": C.sha256_file(C.REPO / RULER), "max_new_tokens": 32, "use_chat_template": True, "limit": args.limit}
        expected_rows = args.limit or 24
    else:
        runner = C.REPO / "scripts" / "run_agentdojo_official_kv.py"
        cmd = [sys.executable, str(runner), "--run-id", out.name, "--model", args.model, "--benchmark-version", "v1.2.2", "--suite", "workspace", "--attack", "injecagent",
               "--methods", args.methods, "--keep-ratios", args.keep_ratios, "--limit-pairs", str(args.limit or 10), "--max-iters", "5", "--max-new-tokens", "128", "--dtype", "bf16",
               "--experiment-config", "configs/acl_main_followup_matrix.json", "--quiet", "--out-dir", str(out)]
        if args.fullkv_run:
            cmd += ["--fullkv-run", args.fullkv_run]
        hyper = {"frozen_runner": "scripts/run_agentdojo_official_kv.py", "benchmark_version": "v1.2.2", "suite": "workspace", "attack": "injecagent", "limit_pairs": 10, "max_iters": 5, "max_new_tokens": 128,
                 "agentdojo_runtime": "external/agentdojo_runtime (vendored, 0.1.35)", "fullkv_run": args.fullkv_run}
        expected_rows = args.limit or 10
    hyper.update({"frozen_runner_sha256": C.sha256_file(runner), "keep_ratios": args.keep_ratios, "methods": args.methods})
    cfg = C.base_config(experiment_id="X6", runner_version="current", model=args.model, dtype="bf16", seed=20260530, keep_ratio=None, variant=args.methods, hyperparams=hyper, extra={"prereg_id": "PREREG-21"})
    C.write_json(out / "config.json", cfg)
    print(" ".join(cmd), flush=True)
    rc = subprocess.call(cmd, cwd=str(C.REPO))
    rows = C.read_jsonl(out / "predictions.jsonl") if (out / "predictions.jsonl").exists() else []
    metrics = json.load((out / "metrics.json").open()) if (out / "metrics.json").exists() else {}
    n_methods = len({(r.get("method"), r.get("keep_ratio")) for r in rows}) if rows else 0
    val = {"exit": rc, "rows": len(rows), "row_count_ok": bool(rows) and len(rows) == expected_rows * n_methods,
           "runtime_errors": sum(1 for r in rows if str(r.get("status", "ok")) not in ("ok", "success")), "empty_outputs": sum(1 for r in rows if str(r.get("status", "ok")) in ("ok", "success") and not str(r.get("output_text", r.get("response", "x"))).strip())}
    rc_cfg = json.load((out / "run_config.json").open()) if (out / "run_config.json").exists() else {}
    cfg["model_revision"] = rc_cfg.get("model_commit")
    summary = {"experiment": "X6", "task": args.bench, "model_tag": args.model_tag, "model": args.model, "methods": args.methods, "metrics_by_method": metrics.get("by_method", {}),
               "validation": val, "valid": rc == 0 and val["row_count_ok"] and val["runtime_errors"] == 0}
    C.write_json(out / "summary.json", summary)
    peak = [r.get("peak_memory_mb") or 0 for r in rows]
    C.write_json(out / "peak_mem.json", {"max_example_peak_memory_mb": max(peak) if peak else None})
    cfg["end_time"] = C.now_iso(); C.write_json(out / "config.json", cfg)
    print(json.dumps({"DONE": str(out), "valid": summary["valid"], "rows": len(rows), "by_method": list(metrics.get("by_method", {}).keys())}), flush=True)
    sys.exit(0 if rc == 0 else rc)


if __name__ == "__main__":
    main()
