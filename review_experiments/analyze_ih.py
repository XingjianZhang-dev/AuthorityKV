"""IH-CacheBench family analysis: per method@ratio counts (reversal / hierarchy / benign, by relation), paired exact
McNemar vs the stored official base and stored full AKV of the same model/scorer/ratio, Holm within a family.
Frozen statistics helpers are imported from scripts/summarize_acl_main_runs.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import akv_common as C  # noqa: E402

RES = C.REPO / "results" / "authoritykv"
RELS = ["system_vs_user", "developer_vs_user", "system_vs_tool", "developer_vs_retrieved_document", "multi_tier"]
STATS = C.load_module_by_path("frozen_stats_ih", C.REPO / "scripts" / "summarize_acl_main_runs.py")
JUDGE = C.load_module_by_path("frozen_judge_ih", C.SNAPSHOT_ROOT / "scripts" / "judge_authoritykv.py")

# stored judged rows: (model_tag, scorer) -> (base run, full run)
STORED_IH = {
    ("qwen7b", "h2o"): ("aclmain_20260725v1_qwen7b_h2o_compositions500", "aclmain_20260725v1_qwen7b_h2o_compositions500"),
    ("qwen7b", "knorm"): ("aclmain_20260725v1_qwen7b_official_nonh2o500", "aclmain_20260725v1_qwen7b_knorm_compositions500"),
    ("qwen7b", "streaming"): ("aclmain_20260725v1_qwen7b_official_nonh2o500", "aclmain_20260725v1_qwen7b_streaming_compositions500"),
    ("qwen7b", "snapkv"): ("aclmain_20260725v1_qwen7b_official_nonh2o500", "aclmain_20260725v1_qwen7b_snapkv_compositions500"),
    ("mistral7b", "h2o"): ("aclmain_20260725v1_mistral7b_core_h2o500", "aclmain_20260725v1_mistral7b_core_h2o500"),
    ("mistral7b", "knorm"): ("aclmain_20260725v1_mistral7b_official_nonh2o500", "aclmain_20260725v1_mistral7b_core_compositions500"),
    ("mistral7b", "streaming"): ("aclmain_20260725v1_mistral7b_official_nonh2o500", "aclmain_20260725v1_mistral7b_core_compositions500"),
    ("yi9b", "h2o"): ("aclmain_20260725v1_yi9b_core_h2o500", "aclmain_20260725v1_yi9b_core_h2o500"),
    ("yi9b", "knorm"): ("aclmain_20260725v1_yi9b_official_nonh2o500", "aclmain_20260725v1_yi9b_core_compositions500"),
    ("yi9b", "streaming"): ("aclmain_20260725v1_yi9b_official_nonh2o500", "aclmain_20260725v1_yi9b_core_compositions500"),
}
HELDOUT = {"paraphrase": "paraphrase", "display_label": "display", "option_card": "option"}
_cache: dict[str, list[dict]] = {}


def judged(run_id: str) -> list[dict]:
    if run_id not in _cache:
        p = RES / run_id / "judged_predictions.jsonl"
        if not p.exists():
            p = RES / run_id / "predictions.jsonl"
            _cache[run_id] = [JUDGE.judge_record(r) for r in C.read_jsonl(p)]
        else:
            _cache[run_id] = C.read_jsonl(p)
    return _cache[run_id]


def stored_rows(model_tag: str, scorer: str, method: str, ratio: float, dataset: str) -> dict[str, dict]:
    if "heldout" in dataset:
        surf = next(v for k, v in HELDOUT.items() if k in dataset)
        run = f"aclmain_20260725v1_qwen7b_heldout_{surf}_{'h2o' if scorer == 'h2o' else 'nonh2o'}120"
    elif "natural_short_120" in dataset:
        run = f"aclmain_20260725v1_qwen7b_curve_{'h2o' if scorer == 'h2o' else 'nonh2o'}120"
    else:
        base_run, full_run = STORED_IH.get((model_tag, scorer), (None, None))
        run = base_run if method.startswith("kvpress_") else full_run
    if run is None or not (RES / run).exists():
        return {}
    return {str(r["example_id"]): r for r in judged(run) if r["method"] == method and abs(float(r["keep_ratio"]) - ratio) < 1e-9}


def counts(rows: list[dict]) -> dict:
    conf = [r for r in rows if r["is_conflict"]]
    ben = [r for r in rows if not r["is_conflict"]]
    out = {"n": len(rows), "conflict_n": len(conf), "reversal": sum(r["authority_reversal"] for r in conf), "hierarchy": sum(r["correct"] for r in conf),
           "benign_n": len(ben), "benign_correct": sum(r["correct"] for r in ben), "malformed": sum(r["malformed"] for r in rows),
           "infeasible": sum(1 for r in rows if r["status"] == "infeasible"), "runtime_error": sum(1 for r in rows if r["status"] == "runtime_error"),
           "by_relation": {rel: {"n": sum(1 for r in conf if r["category"] == rel), "reversal": sum(r["authority_reversal"] for r in conf if r["category"] == rel), "correct": sum(r["correct"] for r in conf if r["category"] == rel)} for rel in RELS}}
    return out


def mcnemar(a: dict[str, dict], b: dict[str, dict], field: str, conflict_only: bool = True) -> dict:
    ids = sorted(set(a) & set(b))
    if conflict_only:
        ids = [i for i in ids if a[i]["is_conflict"]]
    n10 = sum(1 for i in ids if a[i][field] and not b[i][field])
    n01 = sum(1 for i in ids if b[i][field] and not a[i][field])
    return {"n": len(ids), "n10": n10, "n01": n01, "p": STATS.exact_mcnemar_p(n10, n01) if ids else None, "a": sum(1 for i in ids if a[i][field]), "b": sum(1 for i in ids if b[i][field])}


def analyze_run(run_dir: Path, admitted: set[str] | None = None) -> dict:
    """admitted: optional example-id subset (FullKV gate); when given, all counts/comparisons use only those ids."""

    summ = json.load((run_dir / "summary.json").open())
    cfg = json.load((run_dir / "config.json").open())
    rows = C.read_jsonl(run_dir / "judged_predictions.jsonl")
    if admitted is not None:
        rows = [r for r in rows if str(r["example_id"]) in admitted]
    model_tag, scorer, dataset = summ["model_tag"], summ["scorer"], summ["task"] and cfg["hyperparams"]["dataset"]
    out = {"run": run_dir.name, "model_tag": model_tag, "scorer": scorer, "tie_break": summ["tie_break"], "dataset": dataset, "cells": {}, "admitted_n": len(admitted) if admitted is not None else None}
    by = {}
    for r in rows:
        by.setdefault((r["method"], round(float(r["keep_ratio"]), 4)), []).append(r)
    for (method, ratio), rs in sorted(by.items()):
        mine = {str(r["example_id"]): r for r in rs}
        cell = {"method": method, "ratio": ratio, "label": rs[0].get("label"), "variant": rs[0].get("variant"), **counts(rs)}
        base = stored_rows(model_tag, scorer, f"kvpress_{scorer}", ratio, dataset)
        full = stored_rows(model_tag, scorer, f"authority_{scorer}_detected_provenance", ratio, dataset)
        if not base:  # in-run reference (new models: base rows generated in the same run)
            base = {str(r["example_id"]): r for r in by.get((f"kvpress_{scorer}", ratio), [])}
        if not full:
            full = {str(r["example_id"]): r for r in by.get((f"authority_{scorer}_detected_provenance", ratio), [])}
        if admitted is not None:
            base = {k: v for k, v in base.items() if k in admitted}
            full = {k: v for k, v in full.items() if k in admitted}
        if base:
            cell["vs_base"] = {"reversal": mcnemar(base, mine, "authority_reversal"), "hierarchy": mcnemar(base, mine, "correct"), "benign": mcnemar(base, mine, "correct", conflict_only=False) if False else None}
            ben_b = {k: v for k, v in base.items() if not v["is_conflict"]}
            ben_m = {k: v for k, v in mine.items() if not v["is_conflict"]}
            cell["vs_base"]["benign"] = mcnemar(ben_b, ben_m, "correct", conflict_only=False)
            cell["base_counts"] = counts(list(base.values()))
        if full:
            cell["vs_full"] = {"reversal": mcnemar(full, mine, "authority_reversal"), "hierarchy": mcnemar(full, mine, "correct")}
            ben_f = {k: v for k, v in full.items() if not v["is_conflict"]}
            ben_m = {k: v for k, v in mine.items() if not v["is_conflict"]}
            cell["vs_full"]["benign"] = mcnemar(ben_f, ben_m, "correct", conflict_only=False)
            cell["full_counts"] = counts(list(full.values()))
        out["cells"][f"{method}@{ratio:.2f}"] = cell
    return out


def holm_family(cells: list[dict], key: str) -> None:
    """Attach Holm-adjusted p-values for the given comparison key ('vs_base'/'vs_full') across the given cells."""

    ps = [(c, c[key]["reversal"]["p"]) for c in cells if c.get(key) and c[key]["reversal"]["p"] is not None]
    adj = STATS.holm_adjust([p for _, p in ps])
    for (c, _), a in zip(ps, adj):
        c[key]["reversal"]["p_holm"] = a


def fmt_cell(c: dict) -> str:
    rel = " / ".join(f"{c['by_relation'][r]['reversal']}" for r in RELS)
    return f"{c['reversal']}/{c['conflict_n']} | {c['hierarchy']}/{c['conflict_n']} | {c['benign_correct']}/{c['benign_n']} | {rel} | mal {c['malformed']}, inf {c['infeasible']}"


def fmt_p(m: dict | None) -> str:
    if not m:
        return "—"
    s = f"n10={m['n10']}, n01={m['n01']}, p={m['p']:.2g}"
    if "p_holm" in m:
        s += f" (Holm {m['p_holm']:.2g})"
    return s
