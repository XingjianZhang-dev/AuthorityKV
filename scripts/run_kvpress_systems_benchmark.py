#!/usr/bin/env python3
"""Run randomized repeated KVPress systems measurements on fixed prompts."""

from __future__ import annotations

import argparse
import json
import random
import shlex
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any

import torch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
for search_path in (str(ROOT), str(SCRIPTS)):
    while search_path in sys.path:
        sys.path.remove(search_path)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SCRIPTS))

from judge_authoritykv import judge_record  # noqa: E402
from run_authoritykv_smoke import find_token_spans  # noqa: E402
from run_kvpress_authority import (  # noqa: E402
    ATTENTION_OUTPUT_METHODS,
    InfeasibleBudgetError,
    VALID_METHODS,
    compact_span_summary,
    file_sha256,
    generate_one,
    git_revision,
    load_jsonl,
    make_press,
    prompt_parts,
    source_digest,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--methods", required=True)
    parser.add_argument("--keep-ratios", default="0.20,0.40")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--warmup-per-setting", type=int, default=1)
    parser.add_argument("--max-new-tokens", type=int, default=16)
    parser.add_argument("--seed", type=int, default=20260530)
    parser.add_argument("--dtype", choices=["bf16", "fp16", "fp32"], default="bf16")
    parser.add_argument("--assistant-prefix", default='{"decision":"')
    parser.add_argument("--stop-after-json-object", action="store_true")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument(
        "--experiment-config",
        default="configs/acl_main_followup_matrix.json",
    )
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def shuffled_settings(
    settings: list[tuple[str, float]],
    seed: int,
    repeat: int,
    example_index: int,
) -> list[tuple[str, float]]:
    """Return a reproducible independent order for one prompt repetition."""

    ordered = list(settings)
    local_seed = seed + 1_000_003 * repeat + 10_007 * example_index
    random.Random(local_seed).shuffle(ordered)
    return ordered


def empty_result(prompt_tokens: int) -> dict[str, Any]:
    return {
        "output_text": "",
        "generated_token_ids": [],
        "generation_tokens": 0,
        "prompt_tokens": prompt_tokens,
        "retained_prompt_tokens": None,
        "retained_prompt_tokens_min": None,
        "retained_prompt_tokens_max": None,
        "prefill_seconds": None,
        "decode_seconds": None,
        "elapsed_seconds": None,
        "decode_tokens_per_second": None,
        "peak_memory_mb": None,
        "press_audit": [],
    }


def group_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[f"{record['method']}@{record['keep_ratio']:.2f}"].append(record)
    by_method: dict[str, Any] = {}
    for key, rows in sorted(groups.items()):
        eligible = [row for row in rows if row.get("status") == "ok"]

        def med(field: str) -> float | None:
            values = [
                float(row[field])
                for row in eligible
                if row.get(field) is not None
            ]
            return median(values) if values else None

        by_method[key] = {
            "method": rows[0]["method"],
            "keep_ratio": rows[0]["keep_ratio"],
            "attempted_num": len(rows),
            "eligible_num": len(eligible),
            "correct_num": sum(bool(row.get("correct")) for row in rows),
            "correct_den": len(rows),
            "runtime_error_num": sum(
                row.get("status") == "runtime_error" for row in rows
            ),
            "infeasible_num": sum(
                row.get("status") == "infeasible" for row in rows
            ),
            "prefill_seconds_median": med("prefill_seconds"),
            "decode_seconds_median": med("decode_seconds"),
            "elapsed_seconds_median": med("elapsed_seconds"),
            "decode_tps_median": med("decode_tokens_per_second"),
            "peak_memory_mb_median": med("peak_memory_mb"),
            "peak_incremental_memory_mb_median": med(
                "peak_incremental_memory_mb"
            ),
            "retained_prompt_tokens_median": med("retained_prompt_tokens"),
        }
    return {"by_method": by_method}


def main() -> None:
    args = parse_args()
    if args.repeats < 1 or args.warmup_per_setting < 0:
        raise SystemExit("repeats must be positive and warmup must be nonnegative")
    methods = parse_csv(args.methods)
    unknown = sorted(set(methods) - VALID_METHODS)
    if unknown:
        raise SystemExit(f"unknown methods: {', '.join(unknown)}")
    ratios = [float(value) for value in parse_csv(args.keep_ratios)]
    if any(not 0 < ratio <= 1 for ratio in ratios):
        raise SystemExit("keep ratios must be in (0, 1]")
    attention_methods = set(methods) & ATTENTION_OUTPUT_METHODS
    non_attention_compressed = (
        set(methods) - ATTENTION_OUTPUT_METHODS - {"fullkv"}
    )
    if attention_methods and non_attention_compressed:
        raise SystemExit("separate H2O and non-H2O systems groups")

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    torch.backends.cuda.matmul.allow_tf32 = True

    from transformers import AutoModelForCausalLM, AutoTokenizer
    import kvpress
    import transformers

    dataset_path = Path(args.dataset)
    examples = load_jsonl(dataset_path, None)
    if not examples:
        raise SystemExit("dataset is empty")
    dtype = {
        "bf16": torch.bfloat16,
        "fp16": torch.float16,
        "fp32": torch.float32,
    }[args.dtype]
    tokenizer = AutoTokenizer.from_pretrained(args.model, use_fast=True)
    if tokenizer.pad_token_id is None and tokenizer.eos_token_id is not None:
        tokenizer.pad_token = tokenizer.eos_token
    model_kwargs: dict[str, Any] = {"dtype": dtype, "device_map": {"": 0}}
    attention_implementation = "eager" if attention_methods else None
    if attention_implementation:
        model_kwargs["attn_implementation"] = attention_implementation
    model = AutoModelForCausalLM.from_pretrained(args.model, **model_kwargs)
    model.eval()

    experiment_config = Path(args.experiment_config)
    if not experiment_config.is_absolute():
        experiment_config = ROOT / experiment_config
    sources = [
        ROOT / "scripts/run_kvpress_systems_benchmark.py",
        ROOT / "scripts/run_kvpress_authority.py",
        ROOT / "scripts/run_authoritykv_smoke.py",
        ROOT / "scripts/judge_authoritykv.py",
        ROOT / "scripts/run_acl_main_followup_gpu_queue.sh",
        ROOT / "authoritykv_experiments/kvpress_authority.py",
    ]
    kvpress_root = ROOT / "external/kvpress"
    if not kvpress_root.exists():
        kvpress_root = ROOT / "external/kvpress_upstream"
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_config = {
        "run_id": args.run_id,
        "start_time": now_iso(),
        "command": " ".join(shlex.quote(part) for part in sys.argv),
        "source_sha256": source_digest(sources),
        "source_hashes": {
            str(path.relative_to(ROOT)): file_sha256(path) for path in sources
        },
        "experiment_config_sha256": file_sha256(experiment_config),
        "kvpress_commit": git_revision(kvpress_root),
        "model": args.model,
        "model_class": type(model).__name__,
        "model_commit": getattr(model.config, "_commit_hash", None),
        "tokenizer_class": type(tokenizer).__name__,
        "dataset": str(dataset_path),
        "dataset_sha256": file_sha256(dataset_path),
        "dataset_rows": len(examples),
        "methods": methods,
        "keep_ratios": ratios,
        "repeats": args.repeats,
        "warmup_per_setting": args.warmup_per_setting,
        "order_protocol": (
            "deterministic independent shuffle per repeat and example"
        ),
        "seed": args.seed,
        "max_new_tokens": args.max_new_tokens,
        "assistant_prefix": args.assistant_prefix,
        "stop_after_json_object": args.stop_after_json_object,
        "dtype": args.dtype,
        "attn_implementation": attention_implementation,
        "gpu": torch.cuda.get_device_name(0),
        "cuda_runtime": torch.version.cuda,
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
        "kvpress_version": getattr(kvpress, "__version__", "not_exposed"),
        "python_version": sys.version,
    }
    write_json(out_dir / "run_config.json", run_config)

    settings: list[tuple[str, float]] = []
    for method in methods:
        if method == "fullkv":
            settings.append((method, 1.0))
        else:
            settings.extend((method, ratio) for ratio in ratios)
    assistant_prefix_ids = [
        int(token)
        for token in tokenizer(
            args.assistant_prefix,
            add_special_tokens=False,
        )["input_ids"]
    ]

    prepared: list[
        tuple[
            dict[str, Any],
            str,
            list[int],
            list[tuple[int, int]],
            list[int],
            str,
            list[dict[str, Any]],
        ]
    ] = []
    for example in examples:
        context_text, context_ids, offsets, suffix_ids, split_mode = prompt_parts(
            tokenizer,
            example,
        )
        spans = find_token_spans(
            context_text,
            offsets,
            example,
            span_source="metadata",
        )
        prepared.append(
            (
                example,
                context_text,
                context_ids,
                offsets,
                suffix_ids,
                split_mode,
                spans,
            )
        )

    # Warm every setting without including warm-up observations in the artifact.
    warm_example, _, warm_context, _, warm_suffix, _, warm_spans = prepared[0]
    for _ in range(args.warmup_per_setting):
        for method, keep_ratio in settings:
            try:
                warm_press = make_press(method, keep_ratio, warm_spans)
                generate_one(
                    model=model,
                    tokenizer=tokenizer,
                    context_ids=warm_context,
                    suffix_ids=warm_suffix,
                    press=warm_press,
                    max_new_tokens=args.max_new_tokens,
                    assistant_prefix_ids=assistant_prefix_ids,
                    stop_after_json_object=args.stop_after_json_object,
                    output_attentions=method in ATTENTION_OUTPUT_METHODS,
                )
            except InfeasibleBudgetError:
                pass

    raw_records: list[dict[str, Any]] = []
    predictions_path = out_dir / "predictions.jsonl"
    judged_path = out_dir / "judged_predictions.jsonl"
    with predictions_path.open("w", encoding="utf-8") as predictions:
        for repeat in range(args.repeats):
            for example_index, prepared_row in enumerate(prepared):
                (
                    example,
                    _,
                    context_ids,
                    _,
                    suffix_ids,
                    split_mode,
                    spans,
                ) = prepared_row
                span_summary = compact_span_summary(spans)
                ordered = shuffled_settings(
                    settings,
                    args.seed,
                    repeat,
                    example_index,
                )
                for order_index, (method, keep_ratio) in enumerate(ordered):
                    status = "ok"
                    error = None
                    infeasible_reason = None
                    baseline_memory_mb = (
                        torch.cuda.memory_allocated(0) / (1024**2)
                    )
                    try:
                        press = make_press(method, keep_ratio, spans)
                        result = generate_one(
                            model=model,
                            tokenizer=tokenizer,
                            context_ids=context_ids,
                            suffix_ids=suffix_ids,
                            press=press,
                            max_new_tokens=args.max_new_tokens,
                            assistant_prefix_ids=assistant_prefix_ids,
                            stop_after_json_object=args.stop_after_json_object,
                            output_attentions=method in ATTENTION_OUTPUT_METHODS,
                        )
                    except InfeasibleBudgetError as exception:
                        status = "infeasible"
                        infeasible_reason = str(exception)
                        result = empty_result(len(context_ids) + len(suffix_ids))
                    except Exception as exception:
                        status = "runtime_error"
                        error = repr(exception)
                        result = empty_result(len(context_ids) + len(suffix_ids))
                    peak = result.get("peak_memory_mb")
                    incremental_peak = (
                        max(0.0, float(peak) - baseline_memory_mb)
                        if peak is not None
                        else None
                    )
                    record = {
                        "run_id": args.run_id,
                        "repeat": repeat,
                        "example_index": example_index,
                        "order_index": order_index,
                        "example_id": example["id"],
                        "category": example.get("category"),
                        "method": method,
                        "keep_ratio": keep_ratio,
                        "model": args.model,
                        "dataset": str(dataset_path),
                        "status": status,
                        "error": error,
                        "infeasible_reason": infeasible_reason,
                        "expected_behavior": example.get("expected_behavior", {}),
                        "judge_rule": example.get("judge_rule", {}),
                        "metadata": example.get("metadata", {}),
                        "prompt_split_mode": split_mode,
                        "authority_token_spans": span_summary,
                        "baseline_memory_mb": round(baseline_memory_mb, 3),
                        "peak_incremental_memory_mb": (
                            round(incremental_peak, 3)
                            if incremental_peak is not None
                            else None
                        ),
                        **result,
                    }
                    raw_records.append(record)
                    predictions.write(
                        json.dumps(record, ensure_ascii=False) + "\n"
                    )
                    predictions.flush()
                    print(
                        json.dumps(
                            {
                                "repeat": repeat,
                                "example": example["id"],
                                "order": order_index,
                                "method": method,
                                "keep_ratio": keep_ratio,
                                "status": status,
                                "error": error,
                            },
                            ensure_ascii=False,
                        ),
                        flush=True,
                    )

    judged_records = [judge_record(record) for record in raw_records]
    with judged_path.open("w", encoding="utf-8") as handle:
        for record in judged_records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    metrics = group_metrics(judged_records)
    metrics["num_rows"] = len(judged_records)
    write_json(out_dir / "metrics.json", metrics)
    run_config["end_time"] = now_iso()
    write_json(out_dir / "run_config.json", run_config)
    print(
        json.dumps(
            {
                "run_dir": str(out_dir),
                "rows": len(judged_records),
                "errors": sum(
                    row.get("status") == "runtime_error"
                    for row in judged_records
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
