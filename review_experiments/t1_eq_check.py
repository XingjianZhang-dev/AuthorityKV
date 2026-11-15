#!/usr/bin/env python3
"""PREREG-25 amendment B check: EQ runs (tie_break=earliest) vs stored R↑ outputs, token by token."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import akv_common as C
RES = C.REPO / "results" / "authoritykv"
IH_STORED = {"knorm": ("aclmain_20260725v1_qwen7b_official_nonh2o500", "aclmain_20260725v1_qwen7b_knorm_compositions500"),
             "streaming": ("aclmain_20260725v1_qwen7b_official_nonh2o500", "aclmain_20260725v1_qwen7b_streaming_compositions500"),
             "h2o": ("aclmain_20260725v1_qwen7b_h2o_compositions500", "aclmain_20260725v1_qwen7b_h2o_compositions500")}
MX = {"knorm": "arrmixed_20260726v4_qwen_knorm40_full300", "streaming": "arrmixed_20260726v4_qwen_streaming_full300"}
SYS = {"knorm": "arrsys_20260726v4_qwen_knorm40_full150", "streaming": "arrsys_20260726v4_qwen_streaming40_full150"}
_c = {}
def load(p):
    if p not in _c:
        _c[p] = {}
        for r in C.read_jsonl(p):
            _c[p][(str(r["example_id"]), r["method"], round(float(r["keep_ratio"]), 4))] = r
    return _c[p]
IH_STORED_M = {"mistral7b": ("aclmain_20260725v1_mistral7b_official_nonh2o500", "aclmain_20260725v1_mistral7b_core_compositions500"),
               "yi9b": ("aclmain_20260725v1_yi9b_official_nonh2o500", "aclmain_20260725v1_yi9b_core_compositions500")}
MODEL = {"m": "qwen7b"}
def ref_path(task, scorer, method):
    if task == "ih" and MODEL["m"] in IH_STORED_M:
        b, f = IH_STORED_M[MODEL["m"]]
        return (RES / b / "predictions.jsonl", f"kvpress_{scorer}") if method.endswith("_basepdempty") else (RES / f / "predictions.jsonl", method)
    if task == "ih":
        if method.endswith("_basepdempty"):
            return RES / IH_STORED[scorer][0] / "predictions.jsonl", f"kvpress_{scorer}"
        if method.endswith("_rpstrict"):
            e3 = [d for d in sorted(C.RUNS_DIR.glob(f"*_E3-E3b-rpstrict-e3b_qwen7b_{scorer}_20-40")) if (d / "summary.json").exists()]
            return e3[-1] / "predictions.jsonl", method
        return RES / IH_STORED[scorer][1] / "predictions.jsonl", method
    if task == "mixed":
        if method == "authority_streaming_detected":
            return RES / "arrmixed_robustfull_20260727v2_qwen_streaming_detector40_300" / "predictions.jsonl", method
        return RES / MX[scorer] / "predictions.jsonl", (f"kvpress_{scorer}" if method.endswith("_basepdempty") else method)
    return RES / SYS[scorer] / "predictions.jsonl", (f"kvpress_{scorer}" if method.endswith("_basepdempty") else method)
tot = {"rows": 0, "equal": 0, "missing_ref": 0}; cells = {}
for run in sorted(C.RUNS_DIR.glob("*_T1EQ*")):
    if not (run / "summary.json").exists():
        continue
    s = json.load(open(run / "summary.json")); task, scorer = s["task"], s["scorer"]; MODEL["m"] = s.get("model_tag", "qwen7b")
    for r in C.read_jsonl(run / "predictions.jsonl"):
        p, m = ref_path(task, scorer, r["method"])
        ref = load(p).get((str(r["example_id"]), m, round(float(r["keep_ratio"]), 4)))
        key = f"{MODEL['m']}|{task}|{scorer}|{r['method']}@{float(r['keep_ratio']):.2f}"
        c = cells.setdefault(key, {"rows": 0, "equal": 0, "retained_equal": 0, "diverge": []})
        c["rows"] += 1; tot["rows"] += 1
        if ref is None:
            tot["missing_ref"] += 1; c.setdefault("missing", 0); c["missing"] += 1; continue
        eq = [int(t) for t in r["generated_token_ids"]] == [int(t) for t in ref["generated_token_ids"]]
        req = r.get("retained_prompt_tokens") == ref.get("retained_prompt_tokens")
        c["equal"] += eq; c["retained_equal"] += req; tot["equal"] += eq
        if not eq and len(c["diverge"]) < 3:
            a, b = r["generated_token_ids"], ref["generated_token_ids"]
            k = next((i for i in range(min(len(a), len(b))) if a[i] != b[i]), min(len(a), len(b)))
            c["diverge"].append({"id": r["example_id"], "first_divergence": k, "new": r["output_text"][:80], "ref": ref["output_text"][:80]})
for k, v in sorted(cells.items()):
    print(k, f"{v['equal']}/{v['rows']} token-identical; retained_count_equal {v['retained_equal']}/{v['rows']}", v.get("missing", ""), v["diverge"] if v["diverge"] else "")
print("TOTAL", tot)
