#!/usr/bin/env python3
"""Selection-only analyses (prefill, no generation).
  --mode a4  (PREREG-09) mixed-evidence retained-set composition: base / full AKV / detector-only × {topk, recency};
             token categories: system, question, answer_sentence, other_evidence, injection (annotated note), template.
  --mode a3  (PREREG-08) Δ constant and numerics: float64 selections for Δ ∈ {2M+ε, 4(M+1), 100(M+1)} vs the real fp32
             selection; within-tier Kendall τ; lexicographic-sort equivalence.
Retained positions are recovered from the frozen compress() output by exact bf16 key-row matching; base scores are
captured by wrapping the frozen scorer's score(); nothing frozen is modified."""

from __future__ import annotations

import argparse
import collections
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import akv_common as C  # noqa: E402
import akv_variants as V  # noqa: E402


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", choices=["a4", "a3"], required=True)
    p.add_argument("--runner", choices=["snapshot", "current"], required=True)
    p.add_argument("--task", choices=["mixed", "ih", "sys"], required=True)
    p.add_argument("--dataset", required=True)
    p.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    p.add_argument("--model-tag", default="qwen7b")
    p.add_argument("--scorer", required=True)
    p.add_argument("--keep-ratios", required=True)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--sample", type=int, default=None, help="a3: sample N examples with seed 20260917")
    p.add_argument("--prereg", required=True)
    p.add_argument("--out-dir", required=True)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out = Path(args.out_dir).resolve(); out.mkdir(parents=True, exist_ok=True)
    runner = C.load_runner(args.runner)
    smoke = sys.modules["run_authoritykv_smoke"]
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, DynamicCache
    import akv_presses as PR
    sys.path.insert(0, str(C.REPO / "scripts"))
    import run_external_utility_kv as U

    ratios = [float(x) for x in args.keep_ratios.split(",")]
    scorer = args.scorer
    eager = scorer == "h2o"
    policy = "priority" if args.task in ("mixed", "sys") else "strict"
    scan_chat = args.task == "mixed"
    cfg = C.base_config(experiment_id=("A4" if args.mode == "a4" else "A3"), runner_version=args.runner, model=args.model, dtype="bf16", seed=20260917, keep_ratio=None,
                        variant=f"selection_only_{args.mode}", hyperparams={"task": args.task, "dataset": args.dataset, "scorer": scorer, "ratios": ratios, "policy": policy, "limit": args.limit, "sample": args.sample,
                                                                             "new_code": {f: C.sha256_file(Path(__file__).resolve().parent / f) for f in ("akv_select.py", "akv_presses.py", "d1_streaming_tiebreak.py")}},
                        extra={"prereg_id": args.prereg})
    C.write_json(out / "config.json", cfg)
    torch.manual_seed(20260917)
    torch.backends.cuda.matmul.allow_tf32 = True
    tok = AutoTokenizer.from_pretrained(args.model, use_fast=True)
    if tok.pad_token_id is None and tok.eos_token_id is not None:
        tok.pad_token = tok.eos_token
    kw = {"dtype": torch.bfloat16, "device_map": {"": 0}}
    if eager:
        kw["attn_implementation"] = "eager"
    model = AutoModelForCausalLM.from_pretrained(args.model, **kw).eval()
    cfg["model_revision"] = getattr(model.config, "_commit_hash", None)
    examples = C.read_jsonl(C.REPO / args.dataset)
    if args.sample:
        rng = random.Random(20260917)
        examples = [examples[i] for i in sorted(rng.sample(range(len(examples)), args.sample))]
    if args.limit:
        examples = examples[: args.limit]
    labels = {str(r["id"]): r for r in C.read_jsonl(C.REPO / "data/mixed_evidence_attack/mixed_evidence_labels.jsonl")} if args.task == "mixed" else {}

    def record(press):
        rec = {}
        scorer_obj = press.base_press if hasattr(press, "base_press") else press
        orig_score = scorer_obj.score
        last = {}

        def sw(module, hidden_states, keys, values, attentions, kwargs):
            sc = orig_score(module, hidden_states, keys, values, attentions, kwargs)
            last["s"] = sc.detach().float()[0].cpu()
            return sc
        scorer_obj.score = sw
        orig = press.compress

        def cw(module, hidden_states, keys, values, attentions, kwargs):
            k_out, v_out = orig(module, hidden_states, keys, values, attentions, kwargs)
            layer = int(getattr(module, "layer_idx", len(rec)))
            kin = keys[0].contiguous().view(torch.int16).cpu().numpy()
            kout = k_out[0].contiguous().view(torch.int16).cpu().numpy()
            sets = []
            for h in range(kin.shape[0]):
                lut = {}
                for pos in range(kin.shape[1]):
                    lut.setdefault(kin[h, pos].tobytes(), []).append(pos)
                positions = [lut.get(kout[h, j].tobytes(), [-1])[0] for j in range(kout.shape[1])]
                sets.append(sorted(positions))
            rec[layer] = {"sets": sets, "scores": last.get("s"), "n": int(keys.shape[2]), "k": int(k_out.shape[2])}
            return k_out, v_out
        press.compress = cw
        return rec

    @torch.inference_mode()
    def prefill(press, context_ids):
        cache = DynamicCache()
        ctx = press(model) if press is not None else torch.no_grad()
        with ctx:
            model.model(input_ids=torch.tensor([context_ids], device=model.device), past_key_values=cache, use_cache=True, output_attentions=eager)

    def mk(method, ratio, spans):
        if args.runner == "current":
            return runner.make_press(method, ratio, spans, strict_protected_budget=(policy == "strict"))
        return runner.make_press(method, ratio, spans)

    records = []
    agg = collections.defaultdict(lambda: collections.defaultdict(list))
    for ei, ex in enumerate(examples):
        context_text, context_ids, offsets, suffix_ids, _ = runner.prompt_parts(tok, ex)
        if args.runner == "current":
            spans = smoke.find_token_spans(context_text, offsets, ex, span_source="metadata", include_low_authority_chat=scan_chat)
        else:
            spans = smoke.find_token_spans(context_text, offsets, ex, span_source="metadata")
        n = len(context_ids)
        # ---------- token categories (a4) ----------
        cats = {}
        if args.mode == "a4":
            cat = ["template"] * n
            sysm = V.chat_message_ranges(context_text, ex, {"system"})
            for m in sysm:
                for i in V.tokens_for_ranges(offsets, [(m["start"], m["end"])]):
                    cat[i] = "system"
            um = V.chat_message_ranges(context_text, ex, {"user"})[0]
            rr = V.retrieved_region(um["text"])
            q = um["text"].rfind("Question:")
            for i in V.tokens_for_ranges(offsets, [(um["start"] + q, um["end"])]):
                cat[i] = "question"
            lab = labels[str(ex["id"])]
            golds = {U.normalize_text(a) for a in lab["answers"]}
            golds = {g for g in golds if g}
            if rr:
                lo, hi = rr
                for i in V.tokens_for_ranges(offsets, [(um["start"] + lo, um["start"] + hi)]):
                    cat[i] = "other_evidence"
                sub = um["text"][lo:hi]
                for s, e, sent in V.sentences_with_offsets(sub):
                    ns = U.normalize_text(sent)
                    if any(g in ns for g in golds):
                        for i in V.tokens_for_ranges(offsets, [(um["start"] + lo + s, um["start"] + lo + e)]):
                            if cat[i] == "other_evidence":
                                cat[i] = "answer_sentence"
            for s in spans:
                if s.get("source") == "metadata_marker":
                    for i in s["token_indices"]:
                        cat[i] = "injection"
            for name in ("system", "question", "answer_sentence", "other_evidence", "injection", "template"):
                cats[name] = [i for i in range(n) if cat[i] == name]
        for ratio in ratios:
            cr = 1 - ratio
            configs = []
            if args.mode == "a4":
                base = runner.build_official_press(f"kvpress_{scorer}", cr)
                full = mk(f"authority_{scorer}_detected_provenance", ratio, spans)
                det = mk(f"authority_{scorer}_detected", ratio, spans)
                configs = [("base", "topk", base), ("full", "topk", full), ("detector_only", "topk", det),
                           ("full", "recency", PR.RecencyTiePress(base_press=runner.build_official_press(f"kvpress_{scorer}", cr), compression_ratio=cr, protected_token_indices=full.protected_token_indices, excluded_token_indices=full.excluded_token_indices, strict_protected_budget=False)),
                           ("detector_only", "recency", PR.RecencyTiePress(base_press=runner.build_official_press(f"kvpress_{scorer}", cr), compression_ratio=cr, protected_token_indices=det.protected_token_indices, excluded_token_indices=det.excluded_token_indices, strict_protected_budget=False))]
            else:
                full = mk(f"authority_{scorer}_detected_provenance", ratio, spans)
                configs = [("full", "topk", full)]
            for name, tie, press in configs:
                rec = record(press)
                try:
                    prefill(press, context_ids)
                except runner.InfeasibleBudgetError as exc:
                    records.append({"example_id": ex["id"], "ratio": ratio, "config": name, "tie_break": tie, "status": "infeasible", "error": str(exc)})
                    continue
                layers = sorted(rec)
                P = set(getattr(press, "protected_token_indices", ())); D = set(getattr(press, "excluded_token_indices", ()))
                B = rec[layers[0]]["k"]
                row = {"example_id": ex["id"], "category": ex.get("category"), "condition": ex.get("metadata", {}).get("condition"), "ratio": ratio, "config": name, "tie_break": tie, "status": "ok",
                       "n_ctx": n, "B": B, "P": len(P), "D": len(D), "overflow": len(P) > B}
                if args.mode == "a4":
                    kept_frac = {}
                    for cname, idx in cats.items():
                        if not idx:
                            kept_frac[cname] = None
                            continue
                        idxs = set(idx)
                        vals = [len(idxs & set(rec[l]["sets"][h])) / len(idxs) for l in layers for h in range(len(rec[l]["sets"]))]
                        kept_frac[cname] = sum(vals) / len(vals)
                    row["kept_fraction"] = kept_frac
                    row["category_sizes"] = {k: len(v) for k, v in cats.items()}
                    row["tier_of_category"] = {k: {"P": len(set(v) & P) / len(v), "D": len(set(v) & D) / len(v), "E": 1 - (len(set(v) & P) + len(set(v) & D)) / len(v)} if v else None for k, v in cats.items()}
                    for cname, val in kept_frac.items():
                        if val is not None:
                            agg[(ratio, row["condition"], name, tie)][cname].append(val)
                else:
                    # ---------- A3 numerics ----------
                    Pt = torch.tensor(sorted(P), dtype=torch.long); Dt = torch.tensor(sorted(D), dtype=torch.long)
                    same_delta = 0; same_fp32 = 0; fp32_diff_at_ties = 0; fp32_diff_total = 0; lex_equal = 0; total_lh = 0
                    tau_P = []; tau_E = []; distinct = []
                    tier = torch.zeros(n, dtype=torch.long)
                    if len(P): tier[Pt] = 2
                    if len(D): tier[Dt] = -1
                    tier = tier + 1  # E=1, P=3, D=0
                    for l in layers:
                        s32 = rec[l]["scores"]  # (h, n) float32
                        s64 = s32.double()
                        adj32 = PR.frozen_adjusted_scores(press, s32.unsqueeze(0), Pt, Dt)[0]
                        M = s64.abs().amax(dim=-1, keepdim=True)
                        eps = 1e-6 * (M + 1.0)
                        deltas = {"2M+eps": 2 * M + eps, "4(M+1)": 4 * (M + 1.0), "100(M+1)": 100 * (M + 1.0)}
                        sel = {}
                        for dn, dv in deltas.items():
                            a = s64.clone()
                            if len(D): a[:, Dt] -= dv
                            if len(P): a[:, Pt] += 2 * dv
                            # deterministic tie rule: adjusted desc, then index asc
                            order = torch.argsort(a, dim=-1, descending=True, stable=True)
                            sel[dn] = [set(order[h, :B].tolist()) for h in range(a.shape[0])]
                        for h in range(s32.shape[0]):
                            total_lh += 1
                            real = set(rec[l]["sets"][h])
                            same_delta += int(sel["2M+eps"][h] == sel["4(M+1)"][h] == sel["100(M+1)"][h])
                            ref = sel["4(M+1)"][h]
                            if real == ref:
                                same_fp32 += 1
                            else:
                                sd = real ^ ref
                                boundary = torch.topk(adj32[h], B).values[-1].item()
                                fp32_diff_total += len(sd)
                                fp32_diff_at_ties += sum(1 for p in sd if adj32[h][p].item() == boundary)
                            # lexicographic sort equivalence: (tier desc, base desc, idx asc)
                            keys_ = sorted(range(n), key=lambda i: (-int(tier[i]), -float(s64[h, i]), i))
                            lex_equal += int(set(keys_[:B]) == ref)
                            distinct.append(len(torch.unique(s32[h])) / n)
                            # Kendall tau-b within tiers between fp32 adjusted order and float64 base order
                            for tname, mask in (("P", tier == 3), ("E", tier == 1)):
                                idx = mask.nonzero(as_tuple=True)[0]
                                if len(idx) < 2:
                                    continue
                                x = adj32[h, idx].double().numpy(); y = s64[h, idx].numpy()
                                try:
                                    from scipy.stats import kendalltau
                                    t = kendalltau(x, y).statistic
                                except Exception:
                                    t = float("nan")
                                (tau_P if tname == "P" else tau_E).append(float(t) if t == t else None)
                    row.update({"layer_heads": total_lh, "delta_sets_identical": same_delta, "fp32_equals_f64_4M1": same_fp32, "fp32_diff_positions": fp32_diff_total, "fp32_diff_at_exact_ties": fp32_diff_at_ties,
                                "lexicographic_equals_offset": lex_equal, "tau_P_mean": (sum(t for t in tau_P if t is not None) / max(1, len([t for t in tau_P if t is not None]))) if tau_P else None,
                                "tau_E_mean": (sum(t for t in tau_E if t is not None) / max(1, len([t for t in tau_E if t is not None]))) if tau_E else None, "tau_E_defined": len([t for t in tau_E if t is not None]),
                                "distinct_score_fraction": sum(distinct) / len(distinct)})
                records.append(row)
                print(json.dumps({k: v for k, v in row.items() if k not in ("kept_fraction", "tier_of_category", "category_sizes")}), flush=True)
    summary = {"mode": args.mode, "task": args.task, "scorer": scorer, "ratios": ratios, "n_examples": len(examples), "records": records, "valid": True}
    if args.mode == "a4":
        summary["aggregate"] = {f"{r}|{c}|{cfg_}|{t}": {k: {"mean": round(sum(v) / len(v), 4), "n": len(v)} for k, v in d.items()} for (r, c, cfg_, t), d in agg.items()}
    C.write_json(out / "summary.json", summary)
    C.write_jsonl(out / "predictions.jsonl", records)
    C.write_json(out / "peak_mem.json", {"max_memory_reserved_mb": round(torch.cuda.max_memory_reserved(0) / 2**20, 1)})
    cfg["end_time"] = C.now_iso(); C.write_json(out / "config.json", cfg)
    print(json.dumps({"DONE": str(out), "n": len(records)}))


if __name__ == "__main__":
    main()
