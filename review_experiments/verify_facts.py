#!/usr/bin/env python3
"""Two-path verification : recompute every line of results/RESPONSE_FACTS.jsonl directly from the
run directories / stored runs with minimal independent code (no analyze_* modules), and report mismatches to
results/_verify_facts_report.json. Exit code 1 on any mismatch."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import akv_common as C  # noqa: E402

RES = C.REPO / "results" / "authoritykv"
sys.path.insert(0, str(C.REPO / "scripts"))
LABELS = {str(r["id"]): r for r in C.read_jsonl(C.REPO / "data/mixed_evidence_attack/mixed_evidence_labels.jsonl")}


def resolve_run(name: str) -> Path:
    p = Path(name)
    if p.is_absolute() and p.exists():
        return p
    if (C.REPO / name).exists():
        return C.REPO / name
    if (RES / name).exists():
        return RES / name
    m = sorted(C.RUNS_DIR.glob(f"*_{name}")) + sorted(C.RUNS_DIR.glob(name))
    if m:
        return m[-1]
    raise FileNotFoundError(name)


def judged_rows(run: Path) -> list[dict]:
    f = run / "judged_predictions.jsonl"
    if f.exists():
        return C.read_jsonl(f)
    # judge on the fly with the snapshot judge (stored base runs have judged files; new runs always write them)
    J = C.load_module_by_path("verify_judge", C.SNAPSHOT_ROOT / "scripts" / "judge_authoritykv.py")
    return [J.judge_record(r) for r in C.read_jsonl(run / "predictions.jsonl")]


def mcnemar_p(n10: int, n01: int) -> float:
    d = n10 + n01
    if d == 0:
        return 1.0
    t = min(n10, n01)
    return min(1.0, 2 * sum(math.comb(d, k) for k in range(t + 1)) / 2**d)


def sel_ih(run, method, ratio, relation=None, population="conflict"):
    rows = [r for r in judged_rows(resolve_run(run)) if r["method"] == method and abs(float(r["keep_ratio"]) - float(ratio)) < 1e-9]
    if population == "conflict":
        rows = [r for r in rows if r["is_conflict"]]
    elif population == "benign":
        rows = [r for r in rows if not r["is_conflict"]]
    if relation:
        rows = [r for r in rows if r["category"] == relation]
    return {str(r["example_id"]): r for r in rows}


def mixed_rows(run, method, ratio, condition, population, task):
    import run_external_utility_kv as U
    rows = [r for r in C.read_jsonl(resolve_run(run) / "predictions.jsonl") if r["method"] == method and abs(float(r["keep_ratio"]) - float(ratio)) < 1e-9]
    out = {}
    if population == "gated64":
        fk = C.read_jsonl(RES / "arrmixed_20260726v1_qwen_fullkv_full300" / "predictions.jsonl")
        ok = {}
        for r in fk:
            lab = LABELS[str(r["example_id"])]
            text = str(r["output_text"])
            good = bool(U.judge_output(text, lab["answers"], "contains_any")["correct"]) and not (lab.get("attack_marker") and lab["attack_marker"].lower() in text.lower())
            ok.setdefault(lab["pair_id"], []).append(good)
        gated = {p for p, v in ok.items() if len(v) == 3 and all(v)}
    for r in rows:
        lab = LABELS[str(r["example_id"])]
        if lab["condition"] != condition:
            continue
        if population == "gated64" and lab["pair_id"] not in gated:
            continue
        if task != "both" and lab["task"] != task:
            continue
        text = str(r["output_text"])
        contains = bool(U.judge_output(text, lab["answers"], "contains_any")["correct"])
        attack = bool(lab.get("attack_marker") and lab["attack_marker"].lower() in text.lower())
        out[str(r["example_id"])] = {"attack": attack, "contains": contains, "joint": contains and not attack, "exact": U.normalize_text(text) in {U.normalize_text(a) for a in lab["answers"]},
                                     "f1": float(U.official_longbench_score(lab["task"], text, lab["answers"]) or 0.0), "gen": int(r.get("generation_tokens", 0))}
    return out


def compute(prov: dict):
    t = prov["type"]
    if t == "ih_count":
        pop = "benign" if prov["field"] == "benign_correct" else ("all" if prov["field"] == "malformed" else "conflict")
        rows = sel_ih(prov["run"], prov["method"], prov["ratio"], prov.get("relation"), pop)
        f = {"reversal": "authority_reversal", "hierarchy": "correct", "benign_correct": "correct", "malformed": "malformed"}[prov["field"]]
        return sum(1 for r in rows.values() if r[f]), len(rows)
    if t == "ih_count_admitted":
        adm = set(json.load((C.REPO / prov["admitted_file"]).open())["admitted_ids"])
        pop = "benign" if prov["field"] == "benign_correct" else "conflict"
        rows = {k: v for k, v in sel_ih(prov["run"], prov["method"], prov["ratio"], prov.get("relation"), pop).items() if k in adm}
        f = {"reversal": "authority_reversal", "hierarchy": "correct", "benign_correct": "correct"}[prov["field"]]
        return sum(1 for r in rows.values() if r[f]), len(rows)
    if t == "ih_mcnemar":
        pop = prov.get("population", "conflict")
        a = sel_ih(prov["run_a"], prov["method_a"], prov["ratio_a"], prov.get("relation"), pop)
        b = sel_ih(prov["run_b"], prov["method_b"], prov["ratio_b"], prov.get("relation"), pop)
        ids = sorted(set(a) & set(b))
        f = prov["field"]
        n10 = sum(1 for i in ids if a[i][f] and not b[i][f]); n01 = sum(1 for i in ids if b[i][f] and not a[i][f])
        return round(mcnemar_p(n10, n01), 6), f"n10={n10},n01={n01},n={len(ids)}"
    if t == "mixed_count":
        rows = mixed_rows(prov["run"], prov["method"], prov["ratio"], prov["condition"], prov["population"], prov.get("task", "both"))
        f = prov["field"]
        if f in ("f1", "gen_mean"):
            key = "f1" if f == "f1" else "gen"
            return (round(sum(r[key] for r in rows.values()) / len(rows), 4) if rows else None), len(rows)
        return sum(1 for r in rows.values() if r[f]), len(rows)
    if t == "mixed_mcnemar":
        a = mixed_rows(prov["run_a"], prov["method_a"], prov["ratio_a"], prov["condition"], prov["population"], prov.get("task", "both"))
        b = mixed_rows(prov["run_b"], prov["method_b"], prov["ratio_b"], prov["condition"], prov["population"], prov.get("task", "both"))
        ids = sorted(set(a) & set(b)); f = prov["field"]
        n10 = sum(1 for i in ids if a[i][f] and not b[i][f]); n01 = sum(1 for i in ids if b[i][f] and not a[i][f])
        return round(mcnemar_p(n10, n01), 6), f"n10={n10},n01={n01},n={len(ids)}"
    if t in ("ihc_count", "ihc_mcnemar"):
        def ihc_rows(run, method, ratio, admitted_from=None):
            rd = resolve_run(run)
            rows = {str(r["example_id"]): r for r in C.read_jsonl(rd / "predictions.jsonl") if r["method"] == method and abs(float(r["keep_ratio"]) - float(ratio)) < 1e-9}
            src = resolve_run(admitted_from) if admitted_from else rd
            adm_file = src / "summary.json"
            if adm_file.exists():
                adm = set(json.load(adm_file.open()).get("admitted_ids", []))
                if adm:
                    rows = {k: v for k, v in rows.items() if k in adm}
            return rows
        if t == "ihc_count":
            rows = ihc_rows(prov["run"], prov["method"], prov["ratio"])
            return sum(1 for r in rows.values() if r[prov["field"]]), len(rows)
        a = ihc_rows(prov["run_a"], prov["method_a"], prov["ratio_a"], prov.get("admitted_from")); b = ihc_rows(prov["run_b"], prov["method_b"], prov["ratio_b"], prov.get("admitted_from"))
        ids = sorted(set(a) & set(b)); f = prov["field"]
        n10 = sum(1 for i in ids if a[i][f] and not b[i][f]); n01 = sum(1 for i in ids if b[i][f] and not a[i][f])
        return round(mcnemar_p(n10, n01), 6), f"n10={n10},n01={n01},n={len(ids)}"
    if t == "sys_count":
        run = resolve_run(prov["run"])
        jf = run / "scored_judgments.jsonl"
        if not jf.exists():
            jf = C.REPO / "reports/arr_august_external_closure/full/system_ifeval_full_v4_judgments.jsonl"
        rows = [r for r in C.read_jsonl(jf) if r["method"] == prov["method"] and abs(float(r["keep_ratio"]) - float(prov["ratio"])) < 1e-9]
        if prov["population"] in ("gated88", "runnable_gated"):
            fk = {r["example_id"] for r in C.read_jsonl(jf) if r["method"] == "fullkv" and r["prompt_strict"]}
            rows = [r for r in rows if r["example_id"] in fk]
        if prov["population"].startswith("runnable"):  # SnapKV/PyramidKV: prompts where both arms ran without the pinned window assertion
            preds = C.read_jsonl(run / "predictions.jsonl")
            base_m = prov.get("base_method", prov["method"])
            ok_m = {str(r["example_id"]) for r in preds if r["method"] == prov["method"] and r.get("status") == "ok"}
            ok_b = {str(r["example_id"]) for r in preds if r["method"] == base_m and r.get("status") == "ok"}
            rows = [r for r in rows if str(r["example_id"]) in ok_m and str(r["example_id"]) in ok_b]
        if prov["field"] == "prompt_strict":
            return sum(1 for r in rows if r["prompt_strict"]), len(rows)
        return sum(sum(r["instruction_strict"]) for r in rows), sum(len(r["instruction_strict"]) for r in rows)
    if t == "sys_mcnemar":
        def rows_for(run, method, ratio):
            rd = resolve_run(run)
            jf = rd / "scored_judgments.jsonl"
            if not jf.exists():
                jf = C.REPO / "reports/arr_august_external_closure/full/system_ifeval_full_v4_judgments.jsonl"
            allj = C.read_jsonl(jf)
            fk = {r["example_id"] for r in allj if r["method"] == "fullkv" and r["prompt_strict"]}
            rows = {r["example_id"]: r for r in allj if r["method"] == method and abs(float(r["keep_ratio"]) - float(ratio)) < 1e-9}
            if prov["population"] == "gated88":
                rows = {k: v for k, v in rows.items() if k in fk}
            return rows
        a = rows_for(prov["run_a"], prov["method_a"], prov["ratio_a"]); b = rows_for(prov["run_b"], prov["method_b"], prov["ratio_b"])
        ids = sorted(set(a) & set(b)); f = prov["field"]
        n10 = sum(1 for i in ids if a[i][f] and not b[i][f]); n01 = sum(1 for i in ids if b[i][f] and not a[i][f])
        return round(mcnemar_p(n10, n01), 6), f"n10={n10},n01={n01},n={len(ids)}"
    if t == "json_value":
        obj = json.load((resolve_run(prov["file"]) if not prov["file"].endswith(".json") else (C.REPO / prov["file"] if (C.REPO / prov["file"]).exists() else resolve_run(Path(prov["file"]).parent.name) / Path(prov["file"]).name)).open())
        cur = obj
        parts = prov["path"] if isinstance(prov["path"], list) else prov["path"].replace("]", "").split(".")
        for part in parts:
            if isinstance(part, int):
                cur = cur[part]
            elif isinstance(part, str) and "[" in part:
                k, i = part.split("[")
                cur = cur[k][int(i)] if k else cur[int(i)]
            else:
                cur = cur[part]
        return cur, "json"
    raise ValueError(t)


def close(a, b) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=1e-3, abs_tol=0.006)
    return str(a) == str(b)


def main() -> int:
    facts = C.read_jsonl(C.REPO / "results" / "RESPONSE_FACTS.jsonl")
    report = {"checked": 0, "ok": 0, "mismatch": [], "errors": [], "at": C.now_iso()}
    for f in facts:
        report["checked"] += 1
        try:
            val, aux = compute(f["provenance"])
        except Exception as exc:  # noqa: BLE001
            report["errors"].append({"id": f["id"], "error": repr(exc)[:300]})
            continue
        ok = close(val, f["number"])
        den = f.get("denominator")
        if aux == "json" or den in (None, ""):
            pass
        elif isinstance(aux, str):
            ok = ok and str(den) == aux
        else:
            ok = ok and close(aux, den)
        if ok:
            report["ok"] += 1
        else:
            report["mismatch"].append({"id": f["id"], "claimed": [f["number"], f.get("denominator")], "recomputed": [val, aux]})
    # robustness label matching check(): recompute the label from the paired facts' own numbers
    import robustness as R
    by = {f["id"]: f for f in facts}
    report["robustness_checked"] = 0
    report["robustness_mismatch"] = []
    for f in facts:
        rb = f.get("robustness")
        if not rb or not rb.get("alt_ids"):
            continue
        report["robustness_checked"] += 1
        alts = [by[i] for i in rb["alt_ids"] if i in by]
        expect = R.label_for(f, alts)
        if expect != rb.get("label"):
            report["robustness_mismatch"].append({"id": f["id"], "claimed": rb.get("label"), "recomputed": expect})
    C.write_json(C.REPO / "results" / "_verify_facts_report.json", report)
    print(json.dumps({k: (v if k != "mismatch" else v[:20]) for k, v in report.items()}, indent=1)[:4000])
    return 1 if report["mismatch"] or report["errors"] or report["robustness_mismatch"] else 0


if __name__ == "__main__":
    sys.exit(main())
