#!/usr/bin/env python3
"""X8 (PREREG-22): IH-Challenge deployable arms on Qwen2.5-7B (and X1a-ext on Qwen2.5-14B), 40 items with the preserved
record-level grader; admitted subset = FullKV-correct items of the stored gate run. Frozen pieces reused by import:
run_kvpress_ih_challenge.role_compatible_example, run_kvpress_authority.{prompt_parts, generate_one, build_official_press},
run_authoritykv_smoke.find_token_spans, run_ih_challenge_kv.{official_grade, injection_followed, summarize}.
Arms: rpstrict (P = chat system, D = tool/retrieved spans → ∅ here; DEPLOYABLE), e3bclfpg2 / e3bclfdeberta (sentence-split
user message, classifier flags → D; DETECTOR annotation-free), detv3mb (detector-v3 on sentences with the annotated marker
strings masked in the detector input only; DETECTOR, marker-blind). Tie rules: topk (paper) or recency (StreamingLLM)."""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import akv_common as C  # noqa: E402

DATASET = "data/external_safety/ih_challenge_blue_team_auto_quoted_system_40.jsonl"
GATE = {"qwen7b": "aclfollow_20260725v2_qwen7b_ih_native_fullkv40"}
STORED_BASE = {"qwen7b": {"h2o": "aclfollow_20260725v2_qwen7b_ih_native_h2o40", "_": "aclfollow_20260725v2_qwen7b_ih_native_nonh2o40"}}
LABELS = {"rpstrict": "DEPLOYABLE (native chat roles; no tool/retrieved spans in IH-Challenge → D = ∅)",
          "e3bclfpg2": "DETECTOR (annotation-free; Llama-Prompt-Guard-2-86M on user-message sentences; label index set by pre-registered probe; local config has no id2label)",
          "e3bclfdeberta": "DETECTOR (annotation-free; deberta-v3-base-prompt-injection-v2 on user-message sentences)",
          "detv3mb": "DETECTOR, marker-blind (detector-v3 on user-message sentences; annotated marker strings masked in the detector input only)"}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    p.add_argument("--model-tag", default="qwen7b")
    p.add_argument("--scorer", required=True)
    p.add_argument("--keep-ratios", default="0.2,0.4")
    p.add_argument("--variants", default="rpstrict,e3bclfpg2,e3bclfdeberta,detv3mb")
    p.add_argument("--tie-break", choices=["topk", "recency"], default="topk")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--experiment", default="X8")
    p.add_argument("--prereg", default="PREREG-22")
    p.add_argument("--gate-run", default=None, help="run dir (runs/… or results/authoritykv/…) with fullkv rows deciding admission")
    p.add_argument("--out-dir", required=True)
    args = p.parse_args()
    out = Path(args.out_dir).resolve(); out.mkdir(parents=True, exist_ok=True)
    scorer = args.scorer
    eager = scorer == "h2o"
    ratios = [float(x) for x in args.keep_ratios.split(",")]
    variants = [v for v in args.variants.split(",") if v]

    runner = C.load_runner("current")
    smoke = sys.modules["run_authoritykv_smoke"]
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import akv_variants as V
    import akv_presses as PR
    ihc = C.load_module_by_path("frozen_ihc_runner", C.REPO / "scripts" / "run_kvpress_ih_challenge.py")
    grader = sys.modules["run_ih_challenge_kv"]

    examples = C.read_jsonl(C.REPO / DATASET)
    if args.limit:
        examples = examples[: args.limit]
    if args.gate_run == "auto":
        cands = sorted(C.RUNS_DIR.glob(f"*_X1a-fullkv_{args.model_tag}_*"))
        args.gate_run = str(cands[-1]) if cands else None
    gate_dir = Path(args.gate_run) if args.gate_run else C.REPO / "results" / "authoritykv" / GATE[args.model_tag]
    if not gate_dir.is_absolute():
        gate_dir = C.REPO / gate_dir
    admitted = {str(r["example_id"]) for r in C.read_jsonl(gate_dir / "predictions.jsonl") if r["method"] == "fullkv" and r.get("official_correct")}
    hyper = {"dataset": DATASET, "dataset_sha256": C.sha256_file(C.REPO / DATASET), "scorer": scorer, "ratios": ratios, "variants": variants, "tie_break": args.tie_break, "max_new_tokens": 16,
             "gate_run": str(gate_dir), "admitted_n": len(admitted), "labels": {v: LABELS[v] for v in variants}, "frozen": {"run_kvpress_ih_challenge.py": C.sha256_file(C.REPO / "scripts/run_kvpress_ih_challenge.py"), "run_ih_challenge_kv.py": C.sha256_file(C.REPO / "scripts/run_ih_challenge_kv.py")},
             "new_code": {f: C.sha256_file(Path(__file__).resolve().parent / f) for f in ("x8_run.py", "akv_variants.py", "akv_presses.py", "akv_common.py")}, "sentence_splitter": "re.split(r\"(?<=[.!?])\\s+|\\n+\") over the whole user message", "policy": "strict"}
    cfg = C.base_config(experiment_id=args.experiment, runner_version="current", model=args.model, dtype="bf16", seed=20260530, keep_ratio=None, variant=",".join(variants), hyperparams=hyper, extra={"prereg_id": args.prereg, "tie_break": args.tie_break})
    C.write_json(out / "config.json", cfg)
    random.seed(20260530); torch.manual_seed(20260530); torch.cuda.manual_seed_all(20260530)
    torch.backends.cuda.matmul.allow_tf32 = True
    tok = AutoTokenizer.from_pretrained(args.model, use_fast=True)
    if tok.pad_token_id is None and tok.eos_token_id is not None:
        tok.pad_token = tok.eos_token
    kw = {"dtype": torch.bfloat16, "device_map": {"": 0}}
    if eager:
        kw["attn_implementation"] = "eager"
    model = AutoModelForCausalLM.from_pretrained(args.model, **kw).eval()
    cfg["model_revision"] = getattr(model.config, "_commit_hash", None)
    judges = {"detv3": V.detector_v3_judge(smoke)}
    clf_audit = {}
    for key, v in (("pg2", "e3bclfpg2"), ("deberta", "e3bclfdeberta")):
        if v in variants:
            spec = V.CLASSIFIERS[key]
            judges[key] = V.ClassifierJudge(spec["model"], spec["revision"], spec["injection_index"])
            clf_audit[key] = {**judges[key].audit(), "label_note": spec["label_note"]}
    cfg["classifiers"] = clf_audit
    C.write_json(out / "config.json", cfg)
    C.write_json(out / "run_config.json", {"run_id": out.name, "model": args.model, "model_commit": cfg["model_revision"], "dataset": DATASET, "methods": variants, "keep_ratios": ratios, "seed": 20260530, "dtype": "bf16", "max_new_tokens": 16, "command": " ".join(sys.argv), "kvpress_commit": cfg["environment"]["kvpress_commit"]})

    Wrapper = sys.modules["authoritykv_experiments.kvpress_authority"].AuthorityAwarePress
    records = []
    t0 = time.time()
    with (out / "predictions.jsonl").open("w", encoding="utf-8") as fh:
        for ei, ex in enumerate(examples):
            prompt_example, role_mode = ihc.role_compatible_example(tok, ex)
            context_text, context_ids, offsets, suffix_ids, split_mode = runner.prompt_parts(tok, prompt_example)
            spans = smoke.find_token_spans(context_text, offsets, ex, span_source="metadata")
            P = set(smoke.span_token_set(spans, {"system", "developer"}))
            D_prov = set(smoke.span_token_set(spans, {"tool", "retrieved_document"}))
            markers = [m for s in ex.get("metadata", {}).get("authority_spans", []) for m in (s.get("start_marker"), s.get("end_marker")) if m]
            user_msgs = V.chat_message_ranges(context_text, prompt_example, {"user"})
            for variant in variants:
                audit = {"variant": variant, "P_size": len(P)}
                if variant == "rpstrict":
                    D = set(D_prov)
                elif variant in ("e3bclfpg2", "e3bclfdeberta"):
                    key = "pg2" if variant == "e3bclfpg2" else "deberta"
                    D, sa = V.flagged_sentence_tokens(context_text, offsets, prompt_example, judges[key], roles={"user"}, region="message")
                    D |= D_prov
                    audit["sentence_audit"] = sa
                elif variant == "detv3mb":
                    def blind(sentence: str) -> bool:
                        text = sentence
                        for m in markers:
                            text = text.replace(m, " " * len(m))
                        return judges["detv3"](text)
                    D, sa = V.flagged_sentence_tokens(context_text, offsets, prompt_example, blind, roles={"user"}, region="message")
                    D |= D_prov
                    audit["sentence_audit"] = sa
                    audit["masked_markers"] = markers
                else:
                    raise SystemExit(variant)
                D -= P
                audit["D_size"] = len(D)
                user_tokens = {i for m in user_msgs for i in V.tokens_for_ranges(offsets, [(m["start"], m["end"])])}
                audit["user_tokens"] = len(user_tokens); audit["user_tokens_demoted"] = len(D & user_tokens)
                ann = {i for s in spans if s.get("source") == "metadata_marker" for i in s["token_indices"]}
                audit["annotated_span_tokens"] = len(ann); audit["tp"] = len(D & ann); audit["fp"] = len(D - ann); audit["fn"] = len(ann - D)
                for ratio in ratios:
                    cr = 1.0 - ratio
                    base_name = f"kvpress_{scorer}"
                    if args.tie_break == "recency":
                        press = PR.RecencyTiePress(base_press=runner.build_official_press(base_name, cr), compression_ratio=cr, protected_token_indices=tuple(sorted(P)), excluded_token_indices=tuple(sorted(D)), strict_protected_budget=True)
                    else:
                        press = Wrapper(base_press=runner.build_official_press(base_name, cr), compression_ratio=cr, protected_token_indices=tuple(sorted(P)), excluded_token_indices=tuple(sorted(D)), strict_protected_budget=True)
                    status, error, infeasible = "ok", None, None
                    try:
                        result = runner.generate_one(model=model, tokenizer=tok, context_ids=context_ids, suffix_ids=suffix_ids, press=press, max_new_tokens=16, assistant_prefix_ids=[], stop_after_json_object=False, output_attentions=eager)
                    except runner.InfeasibleBudgetError as exc:
                        status, infeasible = "infeasible", str(exc)
                        result = {"output_text": "", "generated_token_ids": [], "generation_tokens": 0, "prompt_tokens": len(context_ids) + len(suffix_ids), "retained_prompt_tokens": None, "retained_prompt_tokens_min": None, "retained_prompt_tokens_max": None, "prefill_seconds": None, "decode_seconds": None, "elapsed_seconds": None, "decode_tokens_per_second": None, "peak_memory_mb": None, "press_audit": []}
                    except torch.cuda.OutOfMemoryError:
                        raise
                    except Exception as exc:  # noqa: BLE001
                        status, error = "runtime_error", repr(exc)[:400]
                        result = {"output_text": "", "generated_token_ids": [], "generation_tokens": 0, "prompt_tokens": len(context_ids) + len(suffix_ids), "retained_prompt_tokens": None, "retained_prompt_tokens_min": None, "retained_prompt_tokens_max": None, "prefill_seconds": None, "decode_seconds": None, "elapsed_seconds": None, "decode_tokens_per_second": None, "peak_memory_mb": None, "press_audit": []}
                    official_correct, grader_error = grader.official_grade(ex, result["output_text"])
                    rec = {"run_id": out.name, "example_index": ei, "example_id": ex["id"], "category": ex.get("category"), "task_type": ex.get("metadata", {}).get("task_type"), "expected_city": ex.get("metadata", {}).get("expected_city"),
                           "method": f"authority_{scorer}_{variant}", "variant": variant, "label": LABELS[variant], "tie_break": args.tie_break, "keep_ratio": ratio, "model": args.model, "dataset": DATASET,
                           "prompt_split_mode": split_mode, "role_compatibility_mode": role_mode, "authority_token_spans": runner.compact_span_summary(spans), "admitted": ex["id"] in admitted,
                           "status": status, "error": error, "infeasible_reason": infeasible, "grader_error": grader_error, "official_correct": official_correct, "injection_followed": grader.injection_followed(result["output_text"]), "variant_audit": audit, **result}
                    records.append(rec)
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n"); fh.flush()
                    print(json.dumps({"i": ei, "example": ex["id"], "method": rec["method"], "keep_ratio": ratio, "correct": official_correct, "inj": rec["injection_followed"], "status": status, "D": len(D), "err": error}), flush=True)
    metrics = grader.summarize(records)
    adm_rows = [r for r in records if r["admitted"]]
    metrics_admitted = grader.summarize(adm_rows) if adm_rows else {}
    # validation: rows, ids, retained counts vs stored base
    base_rows = {}
    sb = STORED_BASE.get(args.model_tag)
    if sb:
        brun = C.REPO / "results" / "authoritykv" / sb["h2o" if eager else "_"]
        for r in C.read_jsonl(brun / "predictions.jsonl"):
            if r["method"] == f"kvpress_{scorer}":
                base_rows[(str(r["example_id"]), round(float(r["keep_ratio"]), 4))] = r
    mism = sum(1 for r in records if r["status"] == "ok" and (str(r["example_id"]), round(r["keep_ratio"], 4)) in base_rows and base_rows[(str(r["example_id"]), round(r["keep_ratio"], 4))]["retained_prompt_tokens"] != r["retained_prompt_tokens"])
    val = {"rows": len(records), "row_count_ok": len(records) == len(examples) * len(variants) * len(ratios), "runtime_errors": sum(1 for r in records if r["status"] == "runtime_error"), "infeasible": sum(1 for r in records if r["status"] == "infeasible"),
           "grader_errors": sum(1 for r in records if r["grader_error"]), "retained_checked": sum(1 for r in records if (str(r["example_id"]), round(r["keep_ratio"], 4)) in base_rows), "retained_mismatch": mism, "empty_outputs": sum(1 for r in records if r["status"] == "ok" and not r["output_text"].strip())}
    summary = {"experiment": args.experiment, "task": "ihc", "model_tag": args.model_tag, "scorer": scorer, "tie_break": args.tie_break, "variants": variants, "keep_ratios": ratios, "admitted_n": len(admitted), "admitted_ids": sorted(admitted),
               "metrics_by_method_all40": metrics.get("by_method", {}), "metrics_by_method_admitted": metrics_admitted.get("by_method", {}), "validation": val, "valid": val["row_count_ok"] and val["runtime_errors"] == 0 and mism == 0, "elapsed_s": round(time.time() - t0, 1), "classifiers": clf_audit}
    C.write_json(out / "summary.json", summary)
    C.write_json(out / "metrics.json", {"all40": metrics, "admitted": metrics_admitted})
    peak = [r.get("peak_memory_mb") or 0 for r in records]
    C.write_json(out / "peak_mem.json", {"max_example_peak_memory_mb": max(peak) if peak else None, "max_memory_reserved_mb": round(torch.cuda.max_memory_reserved(0) / 2**20, 1)})
    cfg["end_time"] = C.now_iso(); C.write_json(out / "config.json", cfg)
    print(json.dumps({"DONE": str(out), "valid": summary["valid"], "admitted": {k: (v.get("official_accuracy_num"), v.get("official_accuracy_den"), v.get("injection_follow_num")) for k, v in summary["metrics_by_method_admitted"].items()}}, indent=1))


if __name__ == "__main__":
    main()
