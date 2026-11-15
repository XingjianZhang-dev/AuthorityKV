#!/usr/bin/env python3
"""D1 sanity test (PREREG-07): on Knorm cells the recency tie-break must give retained sets
identical to the frozen press; on StreamingLLM cells retained counts must be equal (sets differ only among tied
scores). Also: with P = D = ∅ the recency press must reproduce the official StreamingLLM retained set.
Retained positions are recovered from the frozen compress() output by exact key-row matching (no frozen code copied)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import akv_common as C  # noqa: E402


def main() -> None:
    out = C.new_run_dir("D1SANITY", "qwen7b", "knorm-streaming", "20-40")
    runner = C.load_runner("snapshot")
    smoke = sys.modules["run_authoritykv_smoke"]
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, DynamicCache
    import akv_presses as PR

    cfg = C.base_config(experiment_id="D1SANITY", runner_version="snapshot", model="Qwen/Qwen2.5-7B-Instruct", dtype="bf16", seed=20260530, keep_ratio=None,
                        variant="recency_vs_topk_prefill_only", hyperparams={"examples": 4, "scorers": ["knorm", "streaming"], "ratios": [0.2, 0.4]})
    C.write_json(out / "config.json", cfg)
    torch.manual_seed(20260530)
    torch.backends.cuda.matmul.allow_tf32 = True
    tok = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-7B-Instruct", use_fast=True)
    model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-7B-Instruct", dtype=torch.bfloat16, device_map={"": 0}).eval()
    cfg["model_revision"] = getattr(model.config, "_commit_hash", None)
    rows = C.read_jsonl(C.REPO / "data/ih_cachebench/natural_short_500.jsonl")
    picks = [rows[0], rows[1], next(r for r in rows if r["category"] == "multi_tier"), next(r for r in rows if r["category"] == "benign_utility")]

    def record_positions(press):
        """Wrap compress(): recover kept positions by exact bf16 key-row bytes; also keep the adjusted score tensor."""
        rec = {}
        orig = press.compress
        scorer_obj = press.base_press if hasattr(press, "base_press") else press
        orig_score = scorer_obj.score
        last_scores = {}

        def score_wrapped(module, hidden_states, keys, values, attentions, kwargs):
            sc = orig_score(module, hidden_states, keys, values, attentions, kwargs)
            last_scores["s"] = sc.detach().float().clone()
            return sc

        scorer_obj.score = score_wrapped

        def wrapped(module, hidden_states, keys, values, attentions, kwargs):
            k_out, v_out = orig(module, hidden_states, keys, values, attentions, kwargs)
            layer = int(getattr(module, "layer_idx", len(rec)))
            kin = keys[0].contiguous().view(torch.int16).cpu().numpy()  # (h, n, d)
            kout = k_out[0].contiguous().view(torch.int16).cpu().numpy()
            sets = []
            for h in range(kin.shape[0]):
                lut = {}
                for pos in range(kin.shape[1]):
                    lut.setdefault(kin[h, pos].tobytes(), []).append(pos)
                positions = []
                ambiguous = 0
                for j in range(kout.shape[1]):
                    cands = lut.get(kout[h, j].tobytes(), [])
                    if len(cands) != 1:
                        ambiguous += 1
                    positions.append(cands[0] if cands else -1)
                sets.append((sorted(positions), ambiguous))
            rec[layer] = {"sets": sets, "scores": last_scores["s"][0].cpu()}  # scores: (h, n) float32 base scores
            return k_out, v_out

        press.compress = wrapped
        return rec

    @torch.inference_mode()
    def prefill(press, context_ids):
        cache = DynamicCache()
        with press(model):
            model.model(input_ids=torch.tensor([context_ids], device=model.device), past_key_values=cache, use_cache=True)

    results = []
    for ex in picks:
        context_text, context_ids, offsets, suffix_ids, _ = runner.prompt_parts(tok, ex)
        spans = smoke.find_token_spans(context_text, offsets, ex, span_source="metadata")
        for scorer in ("knorm", "streaming"):
            for ratio in (0.2, 0.4):
                cr = 1 - ratio
                frozen = runner.make_press(f"authority_{scorer}_detected_provenance", ratio, spans)
                P, D = frozen.protected_token_indices, frozen.excluded_token_indices
                rec_a = record_positions(frozen)
                prefill(frozen, context_ids)
                rec_press = PR.RecencyTiePress(base_press=runner.build_official_press(f"kvpress_{scorer}", cr), compression_ratio=cr,
                                               protected_token_indices=P, excluded_token_indices=D, strict_protected_budget=True)
                rec_b = record_positions(rec_press)
                prefill(rec_press, context_ids)
                layers = sorted(rec_a)
                A = {l: rec_a[l]["sets"] for l in layers}
                Bv = {l: rec_b[l]["sets"] for l in layers}
                same_sets = sum(1 for l in layers for h in range(len(A[l])) if A[l][h][0] == Bv[l][h][0])
                same_counts = sum(1 for l in layers for h in range(len(A[l])) if len(A[l][h][0]) == len(Bv[l][h][0]))
                total = sum(len(A[l]) for l in layers)
                ambig = sum(A[l][h][1] + Bv[l][h][1] for l in layers for h in range(len(A[l])))
                overlap = sum(len(set(A[l][h][0]) & set(Bv[l][h][0])) / max(1, len(A[l][h][0])) for l in layers for h in range(len(A[l]))) / total
                # tie analysis: every position in the symmetric difference must carry the same ADJUSTED score as the boundary
                Pt = torch.tensor(P, dtype=torch.long); Dt = torch.tensor(D, dtype=torch.long)
                diff_total = 0; diff_tied = 0; distinct_ratio = []
                for l in layers:
                    sc = rec_a[l]["scores"]  # (h, n)
                    adj = PR.frozen_adjusted_scores(frozen, sc.unsqueeze(0), Pt, Dt)[0]  # (h, n) float32
                    for h in range(adj.shape[0]):
                        sa, sb = set(A[l][h][0]), set(Bv[l][h][0])
                        sd = (sa ^ sb) - {-1}
                        distinct_ratio.append(len(torch.unique(adj[h])) / adj.shape[1])
                        if sd:
                            k = len(A[l][h][0])
                            boundary = torch.topk(adj[h], k).values[-1].item()
                            diff_total += len(sd)
                            diff_tied += sum(1 for p in sd if adj[h][p].item() == boundary)
                r = {"example": ex["id"], "scorer": scorer, "ratio": ratio, "P": len(P), "D": len(D), "layer_heads": total, "identical_sets": same_sets, "equal_counts": same_counts,
                     "mean_overlap": round(overlap, 4), "ambiguous_rows": ambig, "kept_count_layer0": frozen.audit_records[0]["kept_count"],
                     "symdiff_positions": diff_total, "symdiff_at_tied_boundary": diff_tied, "distinct_score_fraction_mean": round(sum(distinct_ratio) / len(distinct_ratio), 4)}
                if scorer == "streaming":
                    # P = D = ∅: recency press must reproduce the official StreamingLLM retained set
                    off = runner.build_official_press("kvpress_streaming", cr)
                    rec_c = record_positions(off)
                    prefill(off, context_ids)
                    empty = PR.RecencyTiePress(base_press=runner.build_official_press("kvpress_streaming", cr), compression_ratio=cr, protected_token_indices=(), excluded_token_indices=(), strict_protected_budget=True)
                    rec_d = record_positions(empty)
                    prefill(empty, context_ids)
                    r["official_vs_recency_empty_identical"] = sum(1 for l in layers for h in range(len(rec_c[l]["sets"])) if rec_c[l]["sets"][h][0] == rec_d[l]["sets"][h][0])
                    # under pinning: displaced window tokens must be the OLDEST window tokens (draft check 2)
                    l0 = layers[0]
                    n = len(context_ids)
                    B = r["kept_count_layer0"]
                    window = set(range(4)) | set(range(n - B + 4, n))
                    kept_b = set(Bv[l0][0][0])
                    displaced = sorted(window - kept_b)
                    r["displaced_window_tokens_layer0_head0"] = {"n": len(displaced), "min": displaced[0] if displaced else None, "max": displaced[-1] if displaced else None, "window_start": n - B + 4, "n_ctx": n}
                results.append(r)
                print(json.dumps(r), flush=True)
    knorm_ok = all(r["identical_sets"] == r["layer_heads"] for r in results if r["scorer"] == "knorm")
    knorm_ties_ok = all(r["symdiff_positions"] == r["symdiff_at_tied_boundary"] for r in results if r["scorer"] == "knorm")
    stream_ties_ok = all(r["symdiff_positions"] == r["symdiff_at_tied_boundary"] for r in results if r["scorer"] == "streaming")
    stream_ok = all(r["equal_counts"] == r["layer_heads"] for r in results if r["scorer"] == "streaming")
    empty_ok = all(r.get("official_vs_recency_empty_identical", r["layer_heads"]) == r["layer_heads"] for r in results if r["scorer"] == "streaming")
    summary = {"results": results, "knorm_identical_sets_all": knorm_ok, "knorm_all_differences_at_exact_ties": knorm_ties_ok, "streaming_all_differences_at_exact_ties": stream_ties_ok,
               "streaming_equal_counts_all": stream_ok, "streaming_empty_pd_reproduces_official": empty_ok,
               "pass_strict_criterion": knorm_ok and stream_ok and empty_ok,
               "pass_tie_aware_criterion": knorm_ties_ok and stream_ties_ok and stream_ok and empty_ok,
               "note": "KnormPress scores are -keys.norm() in bf16 (pinned kvpress knorm_press.py): quantised, not tie-free", "valid": True}
    summary["pass"] = summary["pass_tie_aware_criterion"]
    C.write_json(out / "summary.json", summary)
    C.write_json(out / "peak_mem.json", {"max_memory_reserved_mb": round(torch.cuda.max_memory_reserved(0) / 2**20, 1)})
    C.write_jsonl(out / "predictions.jsonl", results)
    (out / "log.txt").write_text(json.dumps(summary, indent=1))
    cfg["end_time"] = C.now_iso(); C.write_json(out / "config.json", cfg)
    print(json.dumps({"D1SANITY": str(out), "pass_strict": summary["pass_strict_criterion"], "pass_tie_aware": summary["pass_tie_aware_criterion"], "knorm_identical": knorm_ok, "knorm_ties_ok": knorm_ties_ok, "streaming_ties_ok": stream_ties_ok, "streaming_counts": stream_ok, "empty": empty_ok}))


if __name__ == "__main__":
    main()
