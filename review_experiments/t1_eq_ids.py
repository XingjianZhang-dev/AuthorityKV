#!/usr/bin/env python3
"""Sample the PREREG-25 amendment B id subsets (seed 20260923) into runs/_t1_ids/."""
import json, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import akv_common as C
import analyze_mixed as M
out = C.REPO / "runs" / "_t1_ids"; out.mkdir(parents=True, exist_ok=True)
rng = random.Random(20260923)
ih = C.read_jsonl(C.REPO / "data/ih_cachebench/natural_short_500.jsonl")
by = {}
for r in ih:
    by.setdefault(r["category"], []).append(str(r["id"]))
ih_ids = sorted(i for cat in sorted(by) for i in rng.sample(sorted(by[cat]), 15))
(out / "eq_ih90.txt").write_text("\n".join(ih_ids) + "\n")
g = sorted(M.gated_pairs()); pairs = set(rng.sample(g, 20))
mx_ids = sorted(str(r["id"]) for r in C.read_jsonl(C.REPO / "data/mixed_evidence_attack/mixed_evidence_labels.jsonl") if r["pair_id"] in pairs)
(out / "eq_mixed60.txt").write_text("\n".join(mx_ids) + "\n")
st = C.read_jsonl(C.REPO / "reports/arr_august_external_closure/full/system_ifeval_full_v4_judgments.jsonl")
gated = sorted(str(r["example_id"]) for r in st if r["method"] == "fullkv" and r["prompt_strict"])
sys_ids = sorted(rng.sample(gated, 20))
(out / "eq_sys20.txt").write_text("\n".join(sys_ids) + "\n")
print(len(ih_ids), len(mx_ids), len(sys_ids), {k: len(v) for k, v in by.items()})
