#!/usr/bin/env python3
"""T1 unit tests (PREREG-25 amendment B): the two tie functions against a naive Python reference, on CPU and CUDA,
with heavy exact ties (small integer scores), several shapes and n_sink values; plus CUDA torch.topk set equality with
the earliest-first rule. Writes nothing; prints PASS/FAIL counts."""
import itertools, random, sys
from pathlib import Path
import torch
sys.path.insert(0, str(Path(__file__).resolve().parent))
import akv_common as C
C.load_runner("current")  # binds authoritykv_experiments.kvpress_authority (needed by akv_presses)
from d1_streaming_tiebreak import recency_tiebreak_topk_indices
from akv_presses_t1 import earliest_tiebreak_topk_indices

def ref_recency(row, k, n_sink):
    n = len(row)
    key = lambda i: (-row[i], 0 if i < n_sink else 1, -(i if i >= n_sink else 0), i)  # score desc, sinks first (earlier sink first), then most recent
    return sorted(range(n), key=key)[:k]

def ref_earliest(row, k):
    return sorted(range(len(row)), key=lambda i: (-row[i], i))[:k]

rng = random.Random(20260923)
fails = {"recency": 0, "earliest": 0, "topk_set": 0}; total = 0; topk_checked = 0
devices = ["cpu"] + (["cuda"] if torch.cuda.is_available() else [])
for dev in devices:
    for trial in range(300):
        b, h = 1, rng.choice([1, 4, 8])
        n = rng.choice([5, 17, 64, 300, 2048])
        levels = rng.choice([2, 3, 10, 1000])
        n_sink = rng.choice([0, 1, 4])
        k = rng.randint(1, n)
        x = torch.tensor([[[float(rng.randrange(levels)) for _ in range(n)] for _ in range(h)] for _ in range(b)], dtype=torch.float32, device=dev)
        if rng.random() < 0.3:  # offsets like the frozen rule: some large +2Δ / -Δ blocks
            d = 4.0 * (float(levels) + 1.0)
            idx = rng.sample(range(n), max(1, n // 5)); x[..., idx] += 2 * d
            idx2 = rng.sample(range(n), max(1, n // 7)); x[..., idx2] -= d
        rec = recency_tiebreak_topk_indices(x, k, n_sink).cpu().tolist()
        ear = earliest_tiebreak_topk_indices(x, k).cpu().tolist()
        xl = x.cpu().tolist()
        for hh in range(h):
            total += 1
            if rec[0][hh] != ref_recency(xl[0][hh], k, n_sink):
                fails["recency"] += 1
            if ear[0][hh] != ref_earliest(xl[0][hh], k):
                fails["earliest"] += 1
            if dev == "cuda":
                topk_checked += 1
                if set(x[0, hh].topk(k).indices.cpu().tolist()) != set(ear[0][hh]):
                    fails["topk_set"] += 1
print({"cases": total, "cuda_topk_cases": topk_checked, "fails": fails})
print("PASS" if not any(fails.values()) else "FAIL")
