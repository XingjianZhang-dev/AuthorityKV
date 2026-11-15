#!/usr/bin/env python3
"""Independent recount of the IH headline (PREREG-25): raw predictions.jsonl → frozen judge (judge_authoritykv.judge_record)
→ counts. Shares no aggregation code with build_t1.py / analyze_ih.py (only the frozen judge and file paths)."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import akv_common as C
J = C.load_module_by_path("frozen_judge_recount", C.SNAPSHOT_ROOT / "scripts" / "judge_authoritykv.py")
RES = C.REPO / "results" / "authoritykv"; RUNS = C.RUNS_DIR
STORED = {("qwen7b","h2o"):("aclmain_20260725v1_qwen7b_h2o_compositions500",)*2, ("qwen7b","knorm"):("aclmain_20260725v1_qwen7b_official_nonh2o500","aclmain_20260725v1_qwen7b_knorm_compositions500"),
          ("qwen7b","streaming"):("aclmain_20260725v1_qwen7b_official_nonh2o500","aclmain_20260725v1_qwen7b_streaming_compositions500"),
          ("mistral7b","h2o"):("aclmain_20260725v1_mistral7b_core_h2o500",)*2, ("mistral7b","knorm"):("aclmain_20260725v1_mistral7b_official_nonh2o500","aclmain_20260725v1_mistral7b_core_compositions500"),
          ("mistral7b","streaming"):("aclmain_20260725v1_mistral7b_official_nonh2o500","aclmain_20260725v1_mistral7b_core_compositions500"),
          ("yi9b","h2o"):("aclmain_20260725v1_yi9b_core_h2o500",)*2, ("yi9b","knorm"):("aclmain_20260725v1_yi9b_official_nonh2o500","aclmain_20260725v1_yi9b_core_compositions500"),
          ("yi9b","streaming"):("aclmain_20260725v1_yi9b_official_nonh2o500","aclmain_20260725v1_yi9b_core_compositions500")}
def count(pred_path, method, ratio):
    rev = conf = ben = benok = 0; ids = set()
    for line in open(pred_path):
        r = json.loads(line)
        if r["method"] != method or abs(float(r["keep_ratio"]) - ratio) > 1e-9: continue
        if r["example_id"] in ids: raise SystemExit(f"duplicate id {r['example_id']} in {pred_path}")
        ids.add(r["example_id"]); j = J.judge_record(r)
        if j["is_conflict"]: conf += 1; rev += bool(j["authority_reversal"])
        else: ben += 1; benok += bool(j["correct"])
    return (rev, conf, benok, ben) if ids else None
def down_runs(m, s):
    if m in ("mistral7b", "yi9b"):  # PREREG-25C: only the 32-token reruns are valid for Mistral/Yi
        pats = [f"*_T1a32-ih_{m}_{s}_20-40-recency"]
    else:
        pats = [f"*_T1a-ih*_{m}_{s}_20-40-recency", f"*_D1b-full_{m}_{s}_20-40-recency", f"*_E3-E3b-*_{m}_{s}_20-40-recency"]
    return [d for p in pats for d in sorted(RUNS.glob(p)) if (d / "summary.json").exists()]
def up_rpstrict_runs(m, s):
    pat = f"*_T1a32up-ih_{m}_{s}_20-40-topk" if m in ("mistral7b", "yi9b") else f"*_E3-E3b-*_{m}_{s}_20-40"
    return [d for d in sorted(RUNS.glob(pat)) if (d / "summary.json").exists()]
tot = {}
print("model scorer ratio arm | R_up rev/conf benign | R_down rev/conf benign")
for (m, s), (base_run, comp_run) in STORED.items():
    for ratio in (0.2, 0.4):
        for arm, mu, md in (("base", f"kvpress_{s}", f"authority_{s}_basepdempty"), ("rpstrict", f"authority_{s}_rpstrict", f"authority_{s}_rpstrict"), ("full", f"authority_{s}_detected_provenance", f"authority_{s}_detected_provenance")):
            if arm == "rpstrict":
                up = next((c for d in up_rpstrict_runs(m, s) if (c := count(d / "predictions.jsonl", mu, ratio))), None)
            else:
                up = count(RES / (base_run if arm == "base" else comp_run) / "predictions.jsonl", mu, ratio)
            dn = next((c for d in down_runs(m, s) if (c := count(d / "predictions.jsonl", md, ratio))), None)
            print(m, s, ratio, arm, "|", up, "|", dn)
            for rule, c in (("up", up), ("down", dn)):
                if c:
                    t = tot.setdefault((m, arm, rule), [0, 0, 0, 0, 0])
                    t[0] += c[0]; t[1] += c[1]; t[2] += c[2]; t[3] += c[3]; t[4] += 1
print("\nTOTALS (model, arm, rule): reversal/conflicts, benign/benign_n, cells")
for m in ("qwen7b", "mistral7b", "yi9b", "all"):
    for arm in ("base", "rpstrict", "full"):
        for rule in ("up", "down"):
            keys = [k for k in tot if k[1] == arm and k[2] == rule and (m == "all" or k[0] == m)]
            if keys:
                a = [sum(tot[k][i] for k in keys) for i in range(5)]
                print(m, arm, rule, f"{a[0]}/{a[1]}", f"{a[2]}/{a[3]}", f"cells={a[4]}")
