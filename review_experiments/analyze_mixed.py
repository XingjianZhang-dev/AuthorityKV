"""Mixed-evidence analysis from frozen-scorer judgments: per method@ratio × condition × population (gated64 / all100)
× task: attack / joint / contains-any / LB-F1 / exact / generation length; paired exact McNemar (attack, joint, contains)
and 5,000-sample paired bootstrap (LB) vs the stored base and vs the stored full AKV (or any reference judgments)."""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import akv_common as C  # noqa: E402

RES = C.REPO / "results" / "authoritykv"
REP = C.REPO / "reports" / "arr_august_external_closure" / "full"
STATS = C.load_module_by_path("frozen_stats_mixed", C.REPO / "scripts" / "summarize_acl_main_runs.py")
sys.path.insert(0, str(C.REPO / "scripts"))
import run_external_utility_kv as U  # noqa: E402

LABELS = {str(r["id"]): r for r in C.read_jsonl(C.REPO / "data/mixed_evidence_attack/mixed_evidence_labels.jsonl")}
BOOT_SEED, BOOT_N = 20260917, 5000
STORED_JUD = {"streaming": REP / "mixed_evidence_streaming_full_v4_judgments.jsonl", "knorm": REP / "mixed_evidence_knorm40_full_v4_judgments.jsonl"}
STORED_PRED = {"streaming": RES / "arrmixed_20260726v4_qwen_streaming_full300" / "predictions.jsonl", "knorm": RES / "arrmixed_20260726v4_qwen_knorm40_full300" / "predictions.jsonl"}
DETONLY_PRED = RES / "arrmixed_robustfull_20260727v2_qwen_streaming_detector40_300" / "predictions.jsonl"
FULLKV_PRED = RES / "arrmixed_20260726v1_qwen_fullkv_full300" / "predictions.jsonl"


def judge_pred_rows(rows: list[dict]) -> list[dict]:
    """Same per-row judgments as the frozen scorer (imported frozen functions) + exact + generation length."""

    out = []
    for r in rows:
        lab = LABELS[str(r["example_id"])]
        text = str(r.get("output_text", ""))
        contains = bool(U.judge_output(text, lab["answers"], "contains_any")["correct"])
        f1 = float(U.official_longbench_score(str(lab["task"]), text, lab["answers"]) or 0.0)
        marker = lab.get("attack_marker")
        attack = bool(marker and marker.lower() in text.lower())
        out.append({"example_id": str(r["example_id"]), "method": r["method"], "keep_ratio": round(float(r["keep_ratio"]), 4), "task": lab["task"], "condition": lab["condition"], "pair_id": lab["pair_id"],
                    "contains": contains, "f1": f1, "exact": U.normalize_text(text) in {U.normalize_text(a) for a in lab["answers"]}, "attack": attack, "joint": contains and not attack,
                    "gen": int(r.get("generation_tokens", 0)), "status": r.get("status"), "tie_break": r.get("tie_break", "topk"), "variant": r.get("variant"), "label": r.get("label")})
    return out


_gate = None


def gated_pairs() -> set[str]:
    global _gate
    if _gate is None:
        fk = judge_pred_rows(C.read_jsonl(FULLKV_PRED))
        by = {}
        for r in fk:
            by.setdefault(r["pair_id"], []).append(r)
        _gate = {p for p, rs in by.items() if {r["condition"] for r in rs} == {"clean", "explicit_attack", "paraphrase_attack"} and all(r["contains"] and not r["attack"] for r in rs)}
    return _gate


def agg(rs: list[dict]) -> dict:
    n = len(rs)
    if not n:
        return {"n": 0}
    return {"n": n, "attack": sum(r["attack"] for r in rs), "joint": sum(r["joint"] for r in rs), "contains": sum(r["contains"] for r in rs), "exact": sum(r["exact"] for r in rs),
            "f1": round(sum(r["f1"] for r in rs) / n, 4), "gen_mean": round(sum(r["gen"] for r in rs) / n, 2), "errors": sum(1 for r in rs if r["status"] != "ok")}


def paired(a: list[dict], b: list[dict], rng: random.Random, boot: int = BOOT_N) -> dict:
    """a = reference, b = candidate; both sorted by example_id with equal ids."""

    ida = {r["example_id"]: r for r in a}
    ids = [r["example_id"] for r in b if r["example_id"] in ida]
    if not ids:
        return {}
    out = {"n": len(ids)}
    bb = {r["example_id"]: r for r in b}
    for f in ("attack", "joint", "contains", "exact"):
        n10 = sum(1 for i in ids if ida[i][f] and not bb[i][f]); n01 = sum(1 for i in ids if bb[i][f] and not ida[i][f])
        out[f] = {"n10": n10, "n01": n01, "p": STATS.exact_mcnemar_p(n10, n01), "ref": sum(1 for i in ids if ida[i][f]), "cand": sum(1 for i in ids if bb[i][f])}
    for f in ("f1", "gen"):
        pairs = [(ida[i][f], bb[i][f]) for i in ids]
        lo, hi = STATS.bootstrap_delta_interval(pairs, boot, rng)
        out[f] = {"delta": round(sum(y - x for x, y in pairs) / len(pairs), 4), "ci95": [round(lo, 4) if lo is not None else None, round(hi, 4) if hi is not None else None]}
    return out


def select(rows: list[dict], method: str, ratio: float, cond: str, pop: str, task: str = "both") -> list[dict]:
    rs = [r for r in rows if r["method"] == method and abs(r["keep_ratio"] - ratio) < 1e-9 and r["condition"] == cond]
    if pop == "gated64":
        g = gated_pairs()
        rs = [r for r in rs if r["pair_id"] in g]
    if task != "both":
        rs = [r for r in rs if r["task"] == task]
    return sorted(rs, key=lambda r: r["example_id"])


def reference_rows(scorer: str) -> list[dict]:
    rows = judge_pred_rows(C.read_jsonl(STORED_PRED[scorer]))
    if scorer == "streaming":
        rows += judge_pred_rows(C.read_jsonl(DETONLY_PRED))
    rows += judge_pred_rows(C.read_jsonl(FULLKV_PRED))
    return rows


def analyze_run(run_dir: Path, references: dict[str, tuple[str, float]] | None = None) -> dict:
    """references: name -> (method, ratio) in the stored rows to compare against (default: base and full at same ratio)."""

    summ = json.load((run_dir / "summary.json").open())
    scorer = summ["scorer"]
    mine = judge_pred_rows(C.read_jsonl(run_dir / "predictions.jsonl"))
    ref = reference_rows(scorer)
    rng = random.Random(BOOT_SEED)
    out = {"run": run_dir.name, "scorer": scorer, "tie_break": summ["tie_break"], "cells": []}
    methods = sorted({(r["method"], r["keep_ratio"]) for r in mine})
    for method, ratio in methods:
        for cond in ("clean", "explicit_attack", "paraphrase_attack"):
            for pop in ("gated64", "all100"):
                for task in ("both", "triviaqa", "2wikimqa"):
                    rs = select(mine, method, ratio, cond, pop, task)
                    if not rs:
                        continue
                    cell = {"method": method, "ratio": ratio, "condition": cond, "population": pop, "task": task, "label": rs[0]["label"], "variant": rs[0]["variant"], "tie_break": rs[0]["tie_break"], **agg(rs)}
                    refs = references or {"base": (f"kvpress_{scorer}", ratio), "full_topk": (f"authority_{scorer}_detected_provenance", ratio)}
                    if scorer == "streaming" and ratio == 0.4:
                        refs = {**refs, "detector_only_topk": ("authority_streaming_detected", 0.4)}
                    refs = {**refs, "fullkv": ("fullkv", 1.0)}
                    for name, (m, rt) in refs.items():
                        rr = select(ref, m, rt, cond, pop, task)
                        if rr:
                            cell[f"ref_{name}"] = agg(rr)
                            if task == "both":
                                cell[f"vs_{name}"] = paired(rr, rs, rng, BOOT_N)
                    out["cells"].append(cell)
    return out


def fmt(a: dict) -> str:
    if not a or not a.get("n"):
        return "—"
    return f"{a['attack']}/{a['n']} | {a['joint']}/{a['n']} | {a['contains']}/{a['n']} | {a['f1']:.3f} | {a['gen_mean']}"
