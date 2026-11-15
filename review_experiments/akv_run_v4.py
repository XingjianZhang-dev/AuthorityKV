#!/usr/bin/env python3
"""v4 (2026-09-23T18:30Z, T1/PREREG-25): v3 + --boundary-shrink K (frozen perturb_metadata_spans boundary_shrink_tokens=K; boundary-shrink rows of the metadata-robustness table). Otherwise identical to v3.
v3 (2026-09-17T14:45Z): + --tie-break random with --tie-seed (D2, akv_presses_d2.RandomTiePress); + variant base_pd_empty (AuthorityKV with P=D=∅, the dormant equivalence). v2 = akv_run_v2.py (used by E1/E4/E2/E6/E5 jobs).
v2 (2026-09-17T06:10Z, patched 06:30Z before any v2 run): + P/D/D_extra index ranges in variant_audit; + tova/pyramid support (LayerBudgetAwareAuthorityPress for pyramid). v1 = akv_run.py (used by D1 runs).
Generic generation runner for the review-period experiments (E1, E2, E3, E3b, E4, D1, E6, X-queue).

Reuses the frozen runner by import (prompt_parts, find_token_spans, make_press, generate_one, official presses) and adds
the new P/D variants (akv_variants) and presses (akv_presses). Output rows have the same fields as the frozen runner's
predictions.jsonl (so the frozen judge/scorers work unchanged) plus variant/tie_break/label fields.

Example:
  python review_experiments/akv_run.py --experiment E3 --prereg PREREG-04 --runner snapshot --task ih \
      --model Qwen/Qwen2.5-7B-Instruct --model-tag qwen7b --dataset data/ih_cachebench/natural_short_500.jsonl \
      --scorer knorm --keep-ratios 0.2,0.4 --variants rpstrict --tie-break topk --out-dir runs/_tmp/x
Variants: base fullkv full rp pin detected system_pin all_control_pin rpstrict e3bdet e3bclfdeberta e3bclfpg2
          e4det e4clfdeberta e4clfpg2 e1a e1b e1a_fullkv e1b_fullkv softsigma:<a> softconst:<c> quota:<q> quotad:<q>
"""

from __future__ import annotations

import argparse
import contextlib
import json
import random
import re
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import akv_common as C  # noqa: E402

TASKS = {  # max_new_tokens, assistant_prefix, stop_after_json, seed, policy, scan_chat
    "ih": dict(max_new=16, prefix='{"decision":"', stop_json=True, seed=20260530, policy="strict", scan_chat=False),
    "heldout": dict(max_new=16, prefix='{"decision":"', stop_json=True, seed=20260530, policy="strict", scan_chat=False),
    "curve": dict(max_new=16, prefix='{"decision":"', stop_json=True, seed=20260530, policy="strict", scan_chat=False),
    "mixed": dict(max_new=32, prefix="", stop_json=False, seed=20260726, policy="priority", scan_chat=True),
    "sys": dict(max_new=1024, prefix="", stop_json=False, seed=20260726, policy="priority", scan_chat=False),
    "long8k": dict(max_new=16, prefix='{"decision":"', stop_json=True, seed=20260530, policy="priority", scan_chat=False),
    "ihc": dict(max_new=64, prefix="", stop_json=False, seed=20260530, policy="strict", scan_chat=False),
}
FROZEN_SUFFIX = {"full": "detected_provenance", "rp": "provenance", "pin": "pin", "detected": "detected"}
LABELS = {
    "base": "none (official press)", "fullkv": "none (FullKV)",
    "full": "DETECTOR (annotated boundaries) [IH] / ORACLE+DETECTOR [mixed]", "rp": "DETECTOR (lexical tool gating)",
    "pin": "P-only", "detected": "DETECTOR (annotated boundaries)", "system_pin": "system-only pin", "all_control_pin": "typed control (all levels)",
    "rpstrict": "DEPLOYABLE (typed roles + source provenance; boundaries from benchmark annotation)",
    "e3bdet": "DETECTOR (annotation-free, detector-v3 sentences)", "e3bclfdeberta": "DETECTOR (annotation-free, deberta-v3-base-prompt-injection-v2)",
    "e3bclfpg2": "DETECTOR (annotation-free, Llama-Prompt-Guard-2-86M; label index set by pre-registered probe; local config has no id2label)",
    "e4det": "DETECTOR (annotation-free, detector-v3 sentences in retrieved region)", "e4clfdeberta": "DETECTOR (annotation-free, deberta-v3-base-prompt-injection-v2)",
    "e4clfpg2": "DETECTOR (annotation-free, Llama-Prompt-Guard-2-86M; label index set by pre-registered probe; local config has no id2label)",
    "e1a": "filter-then-compress (a) whole-source deletion + P pin", "e1b": "filter-then-compress (b) same-span deletion + P pin",
    "e1a_fullkv": "sanity: FullKV on (a)-deleted prompt", "e1b_fullkv": "sanity: FullKV on (b)-deleted prompt",
    "base_pd_empty": "none (official press via AuthorityKV with P = D = ∅; D2 base)",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--experiment", required=True)
    p.add_argument("--prereg", required=True)
    p.add_argument("--runner", choices=["snapshot", "current"], required=True)
    p.add_argument("--task", choices=sorted(TASKS), required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--model-tag", required=True)
    p.add_argument("--dataset", required=True)
    p.add_argument("--ids-file", default=None, help="jsonl/txt with example ids to keep (subset)")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--scorer", required=True, help="h2o|knorm|streaming|snapkv|tova|pyramid|none")
    p.add_argument("--keep-ratios", default="0.2,0.4")
    p.add_argument("--variants", required=True)
    p.add_argument("--tie-break", choices=["topk", "recency", "random"], default="topk")
    p.add_argument("--tie-seed", type=int, default=1)
    p.add_argument("--drop-rate", type=float, default=0.0)
    p.add_argument("--boundary-shrink", type=int, default=0)
    p.add_argument("--policy", choices=["strict", "priority"], default=None, help="override task default")
    p.add_argument("--paired-run", default=None, help="stored run dir with the paired full-AKV rows (E1 kept counts, E2 P/D)")
    p.add_argument("--paired-method", default=None)
    p.add_argument("--max-new-tokens", type=int, default=None)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--label-note", default="")
    return p.parse_args()


def load_ids(path: str | None) -> set[str] | None:
    if not path:
        return None
    ids = set()
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("{"):
            ids.add(str(json.loads(line)["id"]))
        else:
            ids.add(line)
    return ids


def delete_ranges(text: str, ranges: list[tuple[int, int]]) -> str:
    """Delete character ranges (relative to text), merging overlaps."""

    if not ranges:
        return text
    rs = sorted(ranges)
    merged = [list(rs[0])]
    for a, b in rs[1:]:
        if a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    out = []
    cur = 0
    for a, b in merged:
        out.append(text[cur:a])
        cur = b
    out.append(text[cur:])
    return "".join(out)


def ranges_of(idx: set[int]) -> list[list[int]]:
    """Compact sorted token index set into [start, end] inclusive ranges."""

    out: list[list[int]] = []
    for i in sorted(idx):
        if out and i == out[-1][1] + 1:
            out[-1][1] = i
        else:
            out.append([i, i])
    return out


def token_char_ranges(offsets, token_ids: set[int]) -> list[tuple[int, int]]:
    return [(offsets[i][0], offsets[i][1]) for i in sorted(token_ids) if i < len(offsets) and not (offsets[i][0] == offsets[i][1] == 0)]


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    task = TASKS[args.task]
    policy = args.policy or task["policy"]
    max_new = args.max_new_tokens or task["max_new"]
    keep_ratios = [float(x) for x in args.keep_ratios.split(",") if x.strip()]
    variants = [v.strip() for v in args.variants.split(",") if v.strip()]
    scorer = args.scorer
    is_eager = scorer == "h2o"
    ids = load_ids(args.ids_file)
    examples = C.read_jsonl(C.REPO / args.dataset)
    if ids is not None:
        examples = [e for e in examples if str(e["id"]) in ids]
    if args.limit:
        examples = examples[: args.limit]
    dataset_sha = C.sha256_file(C.REPO / args.dataset)

    runner = C.load_runner(args.runner)
    smoke = sys.modules["run_authoritykv_smoke"]
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import akv_variants as V
    import akv_presses as PR
    import akv_presses_d2 as PD

    hyper = {
        "task": args.task, "dataset": args.dataset, "dataset_sha256": dataset_sha, "n_examples": len(examples), "ids_file": args.ids_file, "limit": args.limit,
        "scorer": scorer, "keep_ratios": keep_ratios, "variants": variants, "tie_break": args.tie_break, "drop_rate": args.drop_rate, "boundary_shrink": args.boundary_shrink,
        "policy": policy, "scan_low_authority_chat": task["scan_chat"], "max_new_tokens": max_new, "assistant_prefix": task["prefix"],
        "stop_after_json_object": task["stop_json"], "paired_run": args.paired_run, "paired_method": args.paired_method,
        "labels": {v: LABELS.get(v.split(":")[0], "E2 soft/quota (same P/D as full AKV)") for v in variants}, "label_note": args.label_note,
        "attn_implementation": "eager" if is_eager else "default(sdpa)",
        "new_code": {f: C.sha256_file(Path(__file__).resolve().parent / f) for f in ("akv_run_v4.py", "akv_variants.py", "akv_presses.py", "akv_presses_d2.py", "d1_streaming_tiebreak.py", "akv_common.py")}, "tie_seed": args.tie_seed,
    }
    cfg = C.base_config(experiment_id=args.experiment, runner_version=args.runner, model=args.model, dtype="bf16", seed=task["seed"], keep_ratio=None,
                        variant=",".join(variants), hyperparams=hyper, extra={"prereg_id": args.prereg, "tie_break": args.tie_break})
    C.write_json(out_dir / "config.json", cfg)

    random.seed(task["seed"])
    torch.manual_seed(task["seed"])
    torch.cuda.manual_seed_all(task["seed"])
    torch.backends.cuda.matmul.allow_tf32 = True
    tokenizer = AutoTokenizer.from_pretrained(args.model, use_fast=True)
    if tokenizer.pad_token_id is None and tokenizer.eos_token_id is not None:
        tokenizer.pad_token = tokenizer.eos_token
    kwargs: dict[str, Any] = {"dtype": torch.bfloat16, "device_map": {"": 0}}
    if is_eager:
        kwargs["attn_implementation"] = "eager"
    model = AutoModelForCausalLM.from_pretrained(args.model, **kwargs)
    model.eval()
    cfg["model_revision"] = getattr(model.config, "_commit_hash", None)
    cfg["tokenizer_revision"] = getattr(tokenizer, "init_kwargs", {}).get("_commit_hash")
    C.write_json(out_dir / "config.json", cfg)
    # a minimal run_config.json so the frozen judge CLI can run on this directory if needed
    C.write_json(out_dir / "run_config.json", {"run_id": out_dir.name, "model": args.model, "model_commit": cfg["model_revision"], "dataset": args.dataset,
                                               "dataset_sha256": dataset_sha, "methods": variants, "keep_ratios": keep_ratios, "seed": task["seed"], "dtype": "bf16",
                                               "max_new_tokens": max_new, "command": " ".join(sys.argv), "source_hashes": cfg["runner_source_sha256"], "kvpress_commit": cfg["environment"]["kvpress_commit"]})

    # classifiers
    judges: dict[str, Any] = {"detv3": V.detector_v3_judge(smoke)}
    clf_audit = {}
    need = set()
    for v in variants:
        if v.endswith("clfdeberta"):
            need.add("deberta")
        if v.endswith("clfpg2"):
            need.add("pg2")
    for key in sorted(need):
        spec = V.CLASSIFIERS[key]
        judges[key] = V.ClassifierJudge(spec["model"], spec["revision"], spec["injection_index"])
        clf_audit[key] = {**judges[key].audit(), "label_note": spec["label_note"]}
    cfg["classifiers"] = clf_audit
    C.write_json(out_dir / "config.json", cfg)

    # paired rows (E1 kept counts / validation)
    paired: dict[tuple[str, float], dict] = {}
    if args.paired_run:
        for r in C.read_jsonl(C.REPO / args.paired_run / "predictions.jsonl"):
            if args.paired_method and r["method"] != args.paired_method:
                continue
            paired[(str(r["example_id"]), round(float(r["keep_ratio"]), 4))] = r

    prefix_ids = [int(t) for t in tokenizer(task["prefix"], add_special_tokens=False)["input_ids"]] if task["prefix"] else []
    attention_methods = runner.ATTENTION_OUTPUT_METHODS

    def frozen_method(variant: str) -> str:
        if variant == "base":
            return f"kvpress_{scorer}"
        if variant == "fullkv":
            return "fullkv"
        if variant == "system_pin":
            return f"system_{scorer}_pin"
        if variant == "all_control_pin":
            return f"all_control_{scorer}_pin"
        return f"authority_{scorer}_{FROZEN_SUFFIX[variant]}"

    def call_make_press(method: str, ratio: float, spans):
        if args.runner == "current":
            return runner.make_press(method, ratio, spans, strict_protected_budget=(policy == "strict"))
        if policy != "strict":
            raise SystemExit("snapshot runner supports strict policy only")
        return runner.make_press(method, ratio, spans)

    def find_spans(context_text, offsets, example):
        if args.runner == "current":
            spans = smoke.find_token_spans(context_text, offsets, example, span_source="metadata", include_low_authority_chat=task["scan_chat"])
            if args.drop_rate or args.boundary_shrink:
                spans = runner.perturb_metadata_spans(spans, example_id=str(example["id"]), seed=task["seed"], drop_rate=args.drop_rate, boundary_shrink_tokens=args.boundary_shrink)
            return spans
        return smoke.find_token_spans(context_text, offsets, example, span_source="metadata")

    def full_sets(spans, ratio):
        press = call_make_press(f"authority_{scorer}_detected_provenance" if scorer != "none" else "authority_knorm_detected_provenance", ratio, spans)
        return set(press.protected_token_indices), set(press.excluded_token_indices)

    LayerBudgetPress = None
    if scorer == "pyramid":
        import importlib.util as _ilu
        _spec = _ilu.spec_from_file_location("authoritykv_experiments.outcome_informed_authority", C.REPO / "authoritykv_experiments" / "outcome_informed_authority.py")
        _mod = _ilu.module_from_spec(_spec); sys.modules[_spec.name] = _mod; _spec.loader.exec_module(_mod)
        LayerBudgetPress = _mod.LayerBudgetAwareAuthorityPress
        hyper["layer_budget_press_sha256"] = C.sha256_file(C.REPO / "authoritykv_experiments" / "outcome_informed_authority.py")

    def make_akv(base_name, cr, P, D, strict, example, wrap=None):
        """Construct the AKV press for the requested tie rule (topk = frozen wrapper; recency; random with seed)."""
        Wrapper = sys.modules["authoritykv_experiments.kvpress_authority"].AuthorityAwarePress
        if args.tie_break == "recency":
            return PR.RecencyTiePress(base_press=runner.build_official_press(base_name, cr), compression_ratio=cr, protected_token_indices=tuple(sorted(P)), excluded_token_indices=tuple(sorted(D)), strict_protected_budget=strict)
        if args.tie_break == "random":
            return PD.RandomTiePress(base_press=runner.build_official_press(base_name, cr), compression_ratio=cr, protected_token_indices=tuple(sorted(P)), excluded_token_indices=tuple(sorted(D)), strict_protected_budget=strict, tie_seed=args.tie_seed, example_id=str(example["id"]))
        W = wrap or Wrapper
        return W(base_press=runner.build_official_press(base_name, cr), compression_ratio=cr, protected_token_indices=tuple(sorted(P)), excluded_token_indices=tuple(sorted(D)), strict_protected_budget=strict)

    def build_press(variant: str, ratio: float, spans, context_text, offsets, example):
        """Return (press, method_name, audit, generation_inputs_override)."""

        Wrapper = sys.modules["authoritykv_experiments.kvpress_authority"].AuthorityAwarePress
        if variant == "base_pd_empty":
            press = make_akv(f"kvpress_{scorer}", 1.0 - ratio, set(), set(), False, example)
            return press, f"authority_{scorer}_basepdempty", {"P_size": 0, "D_size": 0}, None
        base_name = f"kvpress_{scorer}"
        cr = 1.0 - ratio
        strict = policy == "strict"
        audit: dict[str, Any] = {}
        if variant in ("base", "fullkv") or variant.endswith("_fullkv") and variant.startswith("e1"):
            pass
        if variant == "fullkv":
            return None, "fullkv", audit, None
        if variant == "base":
            return runner.build_official_press(base_name, cr), base_name, audit, None
        if variant in FROZEN_SUFFIX or variant in ("system_pin", "all_control_pin"):
            method = frozen_method(variant)
            if scorer in ("tova", "pyramid"):
                # P/D sets come from the frozen make_press logic on a composable scorer name; the base press is the requested one.
                proxy = call_make_press(method.replace(f"_{scorer}_", "_snapkv_"), ratio, spans)
                Wrap = LayerBudgetPress if scorer == "pyramid" else Wrapper
                press = Wrap(base_press=runner.build_official_press(base_name, cr), compression_ratio=cr, protected_token_indices=proxy.protected_token_indices,
                             excluded_token_indices=proxy.excluded_token_indices, strict_protected_budget=strict)
            else:
                press = call_make_press(method, ratio, spans)
            if args.tie_break in ("recency", "random"):
                press = make_akv(base_name, cr, set(press.protected_token_indices), set(press.excluded_token_indices), strict, example)
            audit = {"P_size": len(press.protected_token_indices), "D_size": len(press.excluded_token_indices)}
            return press, method, audit, None
        if variant.split(":")[0] in ("softsigma", "softconst", "quota", "quotad"):
            rule, strength = variant.split(":")
            P, D = full_sets(spans, ratio)
            press = PR.SoftQuotaPress(base_press=runner.build_official_press(base_name, cr), compression_ratio=cr, protected_token_indices=tuple(sorted(P)),
                                      excluded_token_indices=tuple(sorted(D)), strict_protected_budget=False, rule=rule, strength=float(strength), tie_break=args.tie_break)
            audit = {"P_size": len(P), "D_size": len(D), "rule": rule, "strength": float(strength)}
            return press, f"authority_{scorer}_{rule}{strength}", audit, None
        if variant.startswith("e1"):
            return build_e1(variant, ratio, spans, context_text, offsets, example)
        P, D, audit = V.build_sets(variant, scorer, spans, context_text, offsets, example, smoke, judges)
        audit["P_ranges"] = ranges_of(P)
        audit["D_ranges"] = ranges_of(D)
        base_D = set(smoke.span_token_set(spans, {"tool", "retrieved_document"})) if variant.startswith("e3b") or variant == "rpstrict" else set()
        audit["D_extra_ranges"] = ranges_of(D - base_D)
        if args.tie_break != "topk" and scorer == "pyramid":
            raise SystemExit("alternative tie rules are not defined for PyramidKV layer budgets")
        press = make_akv(base_name, cr, P, D, strict, example, wrap=(LayerBudgetPress if scorer == "pyramid" else None))
        return press, f"authority_{scorer}_{variant}", audit, None

    def build_e1(variant: str, ratio: float, spans, context_text, offsets, example):
        """E1 filter-then-compress: delete text, re-tokenize, P pinned, D=∅, per-layer kept counts from the paired full run."""

        kind = variant.split("_")[0]  # e1a / e1b
        msgs = V.chat_message_ranges(context_text, example, {"user", "tool", "system", "developer"})
        # which char ranges (in context_text) to delete
        if kind == "e1a":
            del_tokens = {i for s in spans if s.get("level") in ("tool", "retrieved_document") and s.get("source") == "metadata_marker" for i in s["token_indices"]}
            if args.task == "mixed":
                for m in msgs:
                    if m["role"] == "user":
                        rr = V.retrieved_region(m["text"])
                        if rr:
                            del_ranges_ctx = [(m["start"] + rr[0], m["start"] + rr[1])]
                            break
                else:
                    del_ranges_ctx = []
            else:
                del_ranges_ctx = token_char_ranges(offsets, del_tokens)
        else:
            P0, D0 = full_sets(spans, ratio)
            del_ranges_ctx = token_char_ranges(offsets, D0)
        # map to message-relative ranges and rebuild messages
        new_msgs = []
        removed_chars = 0
        for m_index, m in enumerate(example["messages"]):
            content = str(m.get("content", ""))
            loc = next((x for x in msgs if x["index"] == m_index), None)
            if loc is None:
                new_msgs.append(dict(m))
                continue
            rel = [(max(0, a - loc["start"]), min(len(content), b - loc["start"])) for a, b in del_ranges_ctx if b > loc["start"] and a < loc["end"]]
            new_content = delete_ranges(content, rel) if rel else content
            removed_chars += len(content) - len(new_content)
            new_msgs.append({**m, "content": new_content})
        new_example = {**example, "messages": new_msgs}
        ctx2, ids2, off2, suf2, _ = runner.prompt_parts(tokenizer, new_example)
        spans2 = find_spans(ctx2, off2, new_example)
        P2 = set(smoke.span_token_set(spans2, {"system", "developer"}))
        audit = {"kind": kind, "removed_chars": removed_chars, "orig_context_tokens": len(offsets), "new_context_tokens": len(ids2), "P_size": len(P2), "D_size": 0}
        if variant.endswith("_fullkv"):
            return None, f"fullkv_{kind}", audit, (ids2, suf2, spans2)
        prow = paired.get((str(example["id"]), round(ratio, 4)))
        if prow is None or not prow.get("press_audit"):
            raise RuntimeError(f"no paired full-AKV audit for {example['id']}@{ratio}")
        counts = {int(a["layer"]): int(a["kept_count"]) for a in prow["press_audit"]}
        press = PR.FixedCountAuthorityPress(base_press=runner.build_official_press(f"kvpress_{scorer}", 1.0 - ratio), compression_ratio=1.0 - ratio,
                                            protected_token_indices=tuple(sorted(P2)), excluded_token_indices=(), strict_protected_budget=(policy == "strict"),
                                            layer_kept_counts=counts, tie_break=args.tie_break)
        audit["paired_kept_count_layer0"] = counts.get(0)
        audit["uncompressed_expected"] = len(ids2) <= counts.get(0, 0)
        return press, f"authority_{scorer}_{kind}", audit, (ids2, suf2, spans2)

    combos = [(v, (1.0 if v in ("fullkv",) or v.endswith("_fullkv") else r)) for v in variants for r in keep_ratios]
    seen = set()
    combos = [c for c in combos if not (c in seen or seen.add(c))]
    predictions_path = out_dir / "predictions.jsonl"
    n_rows = 0
    t_start = time.time()
    with predictions_path.open("w", encoding="utf-8") as fh:
        for ex_index, example in enumerate(examples):
            context_text, context_ids, offsets, suffix_ids, split_mode = runner.prompt_parts(tokenizer, example)
            spans = find_spans(context_text, offsets, example)
            span_summary = runner.compact_span_summary(spans)
            for variant, ratio in combos:
                status, error, infeasible = "ok", None, None
                audit: dict[str, Any] = {}
                method = variant
                gen_ids, gen_suffix, gen_spans = context_ids, suffix_ids, spans
                try:
                    press, method, audit, override = build_press(variant, ratio, spans, context_text, offsets, example)
                    if override is not None:
                        gen_ids, gen_suffix, gen_spans = override
                    result = runner.generate_one(model=model, tokenizer=tokenizer, context_ids=gen_ids, suffix_ids=gen_suffix, press=press, max_new_tokens=max_new,
                                                 assistant_prefix_ids=prefix_ids, stop_after_json_object=task["stop_json"], output_attentions=(scorer == "h2o" and press is not None))
                except runner.InfeasibleBudgetError as exc:
                    status, infeasible = "infeasible", str(exc)
                    result = {"output_text": "", "generated_token_ids": [], "generation_tokens": 0, "prompt_tokens": len(gen_ids) + len(gen_suffix), "retained_prompt_tokens": None,
                              "retained_prompt_tokens_min": None, "retained_prompt_tokens_max": None, "prefill_seconds": None, "decode_seconds": None, "elapsed_seconds": None,
                              "decode_tokens_per_second": None, "peak_memory_mb": None, "press_audit": []}
                except torch.cuda.OutOfMemoryError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    status, error = "runtime_error", repr(exc)[:500]
                    result = {"output_text": "", "generated_token_ids": [], "generation_tokens": 0, "prompt_tokens": len(gen_ids) + len(gen_suffix), "retained_prompt_tokens": 0,
                              "retained_prompt_tokens_min": 0, "retained_prompt_tokens_max": 0, "prefill_seconds": 0.0, "decode_seconds": 0.0, "elapsed_seconds": 0.0,
                              "decode_tokens_per_second": 0.0, "peak_memory_mb": 0.0, "press_audit": []}
                record = {
                    "run_id": out_dir.name, "example_index": ex_index, "example_id": example["id"], "category": example.get("category", "external_utility"),
                    "method": method, "keep_ratio": ratio, "model": args.model, "dataset": args.dataset, "max_new_tokens": max_new, "seed": task["seed"],
                    "status": status, "error": error, "infeasible_reason": infeasible, "expected_behavior": example.get("expected_behavior", {}),
                    "judge_rule": example.get("judge_rule", {}), "metadata": example.get("metadata", {}), "answers": example.get("answers"),
                    "prompt_split_mode": split_mode, "authority_token_spans": runner.compact_span_summary(gen_spans) if gen_spans is not spans else span_summary,
                    "variant": variant, "tie_break": args.tie_break, "tie_seed": args.tie_seed if args.tie_break == "random" else None, "label": LABELS.get(variant.split(":")[0], "E2"), "protected_budget_policy": policy,
                    "scan_low_authority_chat": task["scan_chat"], "metadata_span_drop_rate": args.drop_rate, "metadata_span_boundary_shrink": args.boundary_shrink, "variant_audit": audit, **result,
                }
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                fh.flush()
                n_rows += 1
                print(json.dumps({"i": ex_index, "example": example["id"], "method": method, "keep_ratio": ratio, "status": status, "gen": result["generation_tokens"],
                                  "retained": result.get("retained_prompt_tokens_min"), "P": audit.get("P_size"), "D": audit.get("D_size"), "err": error}), flush=True)
    elapsed = time.time() - t_start

    # ---- post-processing: judge (ih family) + summary + validation ----
    rows = C.read_jsonl(predictions_path)
    summary: dict[str, Any] = {"experiment": args.experiment, "prereg": args.prereg, "task": args.task, "model": args.model, "model_tag": args.model_tag, "scorer": scorer,
                               "tie_break": args.tie_break, "variants": variants, "keep_ratios": keep_ratios, "n_examples": len(examples), "n_rows": n_rows, "elapsed_s": round(elapsed, 1),
                               "labels": hyper["labels"], "classifiers": clf_audit}
    if args.task in ("ih", "heldout", "curve", "long8k"):
        judge = C.load_module_by_path("judge_snapshot", C.SNAPSHOT_ROOT / "scripts" / "judge_authoritykv.py")
        judged = [judge.judge_record(r) for r in rows]
        C.write_jsonl(out_dir / "judged_predictions.jsonl", judged)
        by = {}
        for r in judged:
            key = f"{r['method']}@{float(r['keep_ratio']):.2f}"
            b = by.setdefault(key, {"conflict_n": 0, "hierarchy": 0, "reversal": 0, "benign_n": 0, "benign_correct": 0, "malformed": 0, "infeasible": 0, "runtime_error": 0,
                                    "by_category": {}, "label": r.get("label")})
            cat = b["by_category"].setdefault(r["category"], {"n": 0, "correct": 0, "reversal": 0})
            cat["n"] += 1
            if r["status"] == "infeasible":
                b["infeasible"] += 1
            if r["status"] == "runtime_error":
                b["runtime_error"] += 1
            if r["malformed"]:
                b["malformed"] += 1
            if r["is_conflict"]:
                b["conflict_n"] += 1
                b["hierarchy"] += int(r["correct"])
                b["reversal"] += int(r["authority_reversal"])
                cat["correct"] += int(r["correct"])
                cat["reversal"] += int(r["authority_reversal"])
            else:
                b["benign_n"] += 1
                b["benign_correct"] += int(r["correct"])
                cat["correct"] += int(r["correct"])
        summary["by_method"] = by
    # validation
    expected_ids = [str(e["id"]) for e in examples]
    got = {}
    for r in rows:
        got.setdefault(f"{r['method']}@{float(r['keep_ratio']):.2f}", []).append(str(r["example_id"]))
    val = {"row_count_ok": n_rows == len(examples) * len(combos), "ids_ok": all(v == expected_ids for v in got.values()),
           "empty_outputs": sum(1 for r in rows if r["status"] == "ok" and not r["output_text"].strip()),
           "runtime_errors": sum(1 for r in rows if r["status"] == "runtime_error"), "infeasible": sum(1 for r in rows if r["status"] == "infeasible"),
           "uncompressed_layers_e1": sum(1 for r in rows for a in r.get("press_audit", []) if a.get("uncompressed"))}
    if args.task in ("ih", "heldout", "curve", "long8k"):
        val["malformed"] = sum(1 for r in judged if r["malformed"])
    # retained counts vs paired base (stored) when available
    base_rows = {}
    task_key = args.task
    if args.task == "heldout":
        for _surf in ("paraphrase", "display_label", "option_card"):
            if _surf in args.dataset:
                task_key = f"heldout_{_surf}"
    base_run = C.PAIRED_BASE.get((args.model_tag, task_key, scorer))
    if base_run and (C.REPO / "results/authoritykv" / base_run / "predictions.jsonl").exists():
        for r in C.read_jsonl(C.REPO / "results/authoritykv" / base_run / "predictions.jsonl"):
            if r["method"] == f"kvpress_{scorer}":
                base_rows[(str(r["example_id"]), round(float(r["keep_ratio"]), 4))] = r
    mism = 0
    checked = 0
    for r in rows:
        if r["status"] != "ok" or r["method"].startswith("fullkv") or r["variant"].startswith("e1"):
            continue
        b = base_rows.get((str(r["example_id"]), round(float(r["keep_ratio"]), 4)))
        if b is None:
            continue
        checked += 1
        if r["retained_prompt_tokens"] != b["retained_prompt_tokens"] or r["prompt_tokens"] != b["prompt_tokens"]:
            mism += 1
    val.update({"paired_base_run": base_run, "retained_checked": checked, "retained_mismatch": mism, "retained_ok": mism == 0})
    if args.task in ("ih", "heldout", "curve", "long8k", "mixed", "sys"):
        val["config_complete"] = all(cfg.get(k) is not None for k in ("model_revision", "environment", "runner_source_sha256", "wrapper_source_sha256", "seed")) and cfg["environment"].get("kvpress_commit") is not None
    summary["validation"] = val
    summary["valid"] = bool(val["row_count_ok"] and val["ids_ok"] and val["retained_ok"] and val["runtime_errors"] == 0 and val.get("config_complete", True))
    peak = [r["peak_memory_mb"] for r in rows if r.get("peak_memory_mb")]
    summary["peak_memory_mb"] = max(peak) if peak else None
    C.write_json(out_dir / "summary.json", summary)
    C.write_json(out_dir / "peak_mem.json", {"max_example_peak_memory_mb": summary["peak_memory_mb"], "max_memory_reserved_mb": round(torch.cuda.max_memory_reserved(0) / 2**20, 1)})
    cfg["end_time"] = C.now_iso()
    C.write_json(out_dir / "config.json", cfg)
    print(json.dumps({"DONE": str(out_dir), "valid": summary["valid"], "validation": val, "by_method": {k: {kk: vv for kk, vv in v.items() if kk != "by_category"} for k, v in summary.get("by_method", {}).items()}}, indent=1))


if __name__ == "__main__":
    main()
