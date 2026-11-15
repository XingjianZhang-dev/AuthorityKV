#!/usr/bin/env python3
"""Tie-break robustness labels(). For every fact whose cell involves StreamingLLM or Knorm, find the twin
fact under the alternative tie rule (StreamingLLM: recency run, id with '-rec-'; Knorm: D2 seeded random runs, ids
'D2-…-random{1,2,3}-…') and attach {"alt_rule", "alt_ids", "alt_numbers", "label"}:
  * comparison facts (id contains '-mcnemar-'): ROBUST iff direction (n01 > n10, i.e. candidate better than base) and
    significance (p < 0.05) hold under the paper rule AND under every alternative-rule twin; else TIE-SENSITIVE;
  * count / mean facts: label 'n/a (see alt)' and the alternative-rule numbers are listed side by side.
Facts without any alternative-rule twin yet are marked 'pending-alt'. verify_facts.py recomputes the label from the
same fact numbers (matching check)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import facts as F  # noqa: E402


def parse_mcnemar(f: dict) -> tuple[int, int, float] | None:
    den = str(f.get("denominator", ""))
    m = re.search(r"n10=(\d+),n01=(\d+)", den)
    if not m or not isinstance(f.get("number"), (int, float)):
        return None
    return int(m.group(1)), int(m.group(2)), float(f["number"])


def twins(fid: str, ids: set[str]) -> tuple[str | None, list[str]]:
    """Return (alt_rule, twin ids) for a paper-rule (topk) fact id."""

    if "-rec-" in fid or "random" in fid or fid.endswith("-rec"):
        return None, []
    out = []
    if "streaming" in fid:
        cand = re.sub(r"(streaming\d+)-", r"\1-rec-", fid, count=1)
        if cand != fid and cand in ids:
            out.append(cand)
        # stored System-IFEval Streaming 40% (A6) ↔ D1c recency run (AKV under recency; base = official press, tie-invariant)
        special = {"A6-streaming-mcnemar-gated88": "D1c-mcnemar-base-rec-gated88", "A6-streaming-AKV-gated88": "D1c-rec-gated88"}
        if fid in special and special[fid] in ids:
            out.append(special[fid])
        cand2 = fid.replace("-topk-", "-rec-")
        if cand2 != fid and cand2 in ids:
            out.append(cand2)
        return ("recency", out)
    if "knorm" in fid:
        for s in (1, 2, 3):
            base = re.sub(r"^(E3|E3b|E1|E4|A5|D1a)-", "D2-", fid, count=1).replace("-main-", "-")  # X8 (IH-Challenge) has no D2 twin: D2 covers IH-CacheBench / mixed / System-IFEval only (fixed 20:05Z; X8 Knorm facts stay pending-alt)
            cands = [re.sub(r"(knorm\d+)-", rf"\1-random{s}-", base, count=1), re.sub(r"(knorm\d+)-", rf"\1-random{s}-", fid, count=1)]
            # A5 stored-run mixed facts (A5-str20-… are streaming; knorm mixed facts live under D2-…-expl-<field>)
            if fid.startswith("A6-knorm-"):  # stored System-IFEval Knorm 40% ↔ D2-ifeval seeded random ties (seeds 1–2)
                if "-mcnemar-" in fid:
                    cands.append(f"D2-ifeval-mcnemar-knorm40-random{s}-gated88")
                elif fid.endswith("-gated88"):
                    arm = "base" if "-base-" in fid else "akv"
                    cands.append(f"D2-ifeval-{arm}-knorm40-random{s}-gated88")
            if fid.startswith("A5-") and "knorm40" in fid and "-mcnemar-" not in fid:  # McNemar twins follow the generic pattern
                arm = "base" if "-base-" in fid else "full"
                fld = fid.rsplit("-", 1)[1]
                cands.append(f"D2-{arm}-qwen7b-knorm40-random{s}-expl-{fld}")
            for cand in cands:
                if cand != fid and cand in ids and cand not in out:
                    out.append(cand)
        return ("random seeds 1-3 (D2)", out)
    return None, []


def label_for(f: dict, alts: list[dict]) -> str:
    if not alts:
        return "pending-alt"
    if "-mcnemar-" in f["id"]:
        p = parse_mcnemar(f)
        if p is None:
            return "n/a"
        n10, n01, pv = p
        ok = (n01 > n10 or (n10 > n01)) and pv < 0.05
        direction = 1 if n01 > n10 else (-1 if n10 > n01 else 0)
        any_sig = pv < 0.05
        for a in alts:
            q = parse_mcnemar(a)
            if q is None:
                return "n/a"
            d2 = 1 if q[1] > q[0] else (-1 if q[0] > q[1] else 0)
            ok = ok and d2 == direction and q[2] < 0.05
            any_sig = any_sig or q[2] < 0.05
        if ok:
            return "ROBUST"
        # no significant difference under the paper rule nor under any alternative rule: not an effect claim, so neither
        # ROBUST nor TIE-SENSITIVE applies; reported as 'n.s. (both rules)' (added 20:45Z; binary rule kept for effect claims)
        return "n.s. (both rules)" if not any_sig else "TIE-SENSITIVE"
    return "n/a (count; alt value listed)"


def main() -> None:
    facts = F.load()
    by = {f["id"]: f for f in facts}
    ids = set(by)
    n = 0
    for f in facts:
        cell = str(f.get("cell", "")).lower() + " " + f["id"].lower()
        if "streaming" not in cell and "knorm" not in cell:
            f.pop("robustness", None)
            continue
        rule, tw = twins(f["id"], ids)
        if rule is None:
            f["robustness"] = {"alt_rule": "this fact is itself an alternative-rule value" if ("-rec" in f["id"] or "random" in f["id"]) else None, "alt_ids": [], "alt_numbers": [], "label": "alt-rule value" if ("-rec" in f["id"] or "random" in f["id"]) else "n/a"}
            continue
        alts = [by[t] for t in tw]
        f["robustness"] = {"alt_rule": rule, "alt_ids": tw, "alt_numbers": [f"{a['number']}/{a.get('denominator')}" if isinstance(a.get("denominator"), int) else f"{a['number']} ({a.get('denominator')})" for a in alts], "label": label_for(f, alts)}
        n += 1
    F.upsert(facts)
    labels = {}
    for f in facts:
        lb = f.get("robustness", {}).get("label")
        if lb:
            labels[lb] = labels.get(lb, 0) + 1
    print("robustness:", labels)


if __name__ == "__main__":
    main()
