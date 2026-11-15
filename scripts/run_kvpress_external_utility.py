#!/usr/bin/env python3
"""Evaluate official KVPress methods on public LongBench/RULER utility data."""

from __future__ import annotations

import argparse
import json
import random
import shlex
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
# Executing this file normally adds ``scripts/`` to sys.path before this
# block.  Explicitly reinsert both paths in the required order so a stale
# repository-root module with the same filename cannot shadow the frozen
# implementation under ``scripts/``.
for search_path in (str(ROOT), str(SCRIPTS)):
    while search_path in sys.path:
        sys.path.remove(search_path)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SCRIPTS))

from run_external_utility_kv import (  # noqa: E402
    answers_for,
    judge_output,
    official_longbench_score,
    summarize,
)
from run_kvpress_authority import (  # noqa: E402
    ATTENTION_OUTPUT_METHODS,
    VALID_METHODS,
    file_sha256,
    generate_one,
    git_revision,
    load_jsonl,
    make_press,
    prompt_parts,
    source_digest,
    write_json,
)

H2O_MEMORY_POLICY = ROOT / "configs/acl_utility_h2o_memory_policy.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--methods", required=True)
    parser.add_argument("--keep-ratios", default="0.20,0.40")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-new-tokens", type=int, default=64)
    parser.add_argument("--seed", type=int, default=20260530)
    parser.add_argument("--dtype", choices=["bf16", "fp16", "fp32"], default="bf16")
    parser.add_argument("--attn-implementation", default=None)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument(
        "--experiment-config",
        default="configs/acl_main_experiment_matrix.json",
    )
    parser.add_argument("--use-chat-template", action="store_true")
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def main() -> None:
    args = parse_args()
    methods = parse_csv(args.methods)
    unknown = sorted(set(methods) - VALID_METHODS)
    if unknown:
        raise SystemExit(f"unknown methods: {', '.join(unknown)}")
    keep_ratios = [float(value) for value in parse_csv(args.keep_ratios)]
    if any(not 0 < ratio <= 1 for ratio in keep_ratios):
        raise SystemExit("keep ratios must be in (0, 1]")
    attention_methods = set(methods) & ATTENTION_OUTPUT_METHODS
    non_attention_methods = set(methods) - ATTENTION_OUTPUT_METHODS
    if attention_methods and non_attention_methods:
        raise SystemExit(
            "run H2O/ObservedAttention methods separately because they require eager attention"
        )
    if (
        attention_methods
        and args.attn_implementation is not None
        and args.attn_implementation != "eager"
    ):
        raise SystemExit(
            "H2O/ObservedAttention methods require the official eager "
            "attention implementation"
        )

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    torch.backends.cuda.matmul.allow_tf32 = True

    from transformers import AutoModelForCausalLM, AutoTokenizer
    import kvpress
    import transformers

    dataset_path = Path(args.dataset)
    examples = load_jsonl(dataset_path, args.limit)
    if not examples:
        raise SystemExit("dataset is empty")
    if args.use_chat_template:
        examples = [
            {
                **example,
                "messages": [{"role": "user", "content": str(example["prompt"])}],
            }
            for example in examples
        ]

    attention_implementation = args.attn_implementation
    if attention_implementation is None and attention_methods:
        attention_implementation = "eager"
    model_load_attention_implementation = attention_implementation
    dtype = {
        "bf16": torch.bfloat16,
        "fp16": torch.float16,
        "fp32": torch.float32,
    }[args.dtype]
    tokenizer = AutoTokenizer.from_pretrained(args.model, use_fast=True)
    if tokenizer.pad_token_id is None and tokenizer.eos_token_id is not None:
        tokenizer.pad_token = tokenizer.eos_token
    model_kwargs: dict[str, Any] = {"dtype": dtype, "device_map": {"": 0}}
    if attention_implementation:
        model_kwargs["attn_implementation"] = attention_implementation
    model = AutoModelForCausalLM.from_pretrained(args.model, **model_kwargs)
    model.eval()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    experiment_config = Path(args.experiment_config)
    if not experiment_config.is_absolute():
        experiment_config = ROOT / experiment_config
    sources = [
        ROOT / "scripts/run_kvpress_external_utility.py",
        ROOT / "scripts/run_kvpress_authority.py",
        ROOT / "scripts/run_external_utility_kv.py",
        ROOT / "scripts/run_acl_main_gpu_queue.sh",
        ROOT / "authoritykv_experiments/kvpress_authority.py",
        H2O_MEMORY_POLICY,
    ]
    kvpress_root = ROOT / "external/kvpress"
    if not kvpress_root.exists():
        kvpress_root = ROOT / "external/kvpress_upstream"
    run_config = {
        "run_id": args.run_id,
        "start_time": now_iso(),
        "command": " ".join(shlex.quote(part) for part in sys.argv),
        "source_sha256": source_digest(sources),
        "source_hashes": {
            str(path.relative_to(ROOT)): file_sha256(path) for path in sources
        },
        "experiment_config": str(experiment_config),
        "experiment_config_sha256": (
            file_sha256(experiment_config) if experiment_config.exists() else None
        ),
        "kvpress_commit": git_revision(kvpress_root),
        "model": args.model,
        "model_class": type(model).__name__,
        "model_commit": getattr(model.config, "_commit_hash", None),
        "model_max_position_embeddings": getattr(
            model.config, "max_position_embeddings", None
        ),
        "tokenizer_class": type(tokenizer).__name__,
        "dataset": str(dataset_path),
        "dataset_sha256": file_sha256(dataset_path),
        "dataset_rows": len(examples),
        "methods": methods,
        "keep_ratios": keep_ratios,
        "max_new_tokens": args.max_new_tokens,
        "seed": args.seed,
        "dtype": args.dtype,
        "attn_implementation": attention_implementation,
        "model_load_attn_implementation": (
            model_load_attention_implementation
        ),
        "use_chat_template": args.use_chat_template,
        "authority_spans": "none_by_design_on_external_utility",
        "attention_memory_policy": str(H2O_MEMORY_POLICY),
        "attention_memory_policy_sha256": file_sha256(
            H2O_MEMORY_POLICY
        ),
        "attention_memory_policy_activation": (
            "official_eager_with_model_level_attention_collection_disabled"
            if attention_methods
            else "not_applicable"
        ),
        "model_level_output_attentions_collected": False,
        "gpu": torch.cuda.get_device_name(0),
        "gpu_capability": list(torch.cuda.get_device_capability(0)),
        "cuda_runtime": torch.version.cuda,
        "cudnn_version": torch.backends.cudnn.version(),
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
        "kvpress_version": getattr(kvpress, "__version__", "not_exposed"),
        "python_version": sys.version,
    }
    write_json(out_dir / "run_config.json", run_config)

    combinations: list[tuple[str, float]] = []
    for method in methods:
        if method == "fullkv":
            combinations.append((method, 1.0))
        else:
            combinations.extend((method, ratio) for ratio in keep_ratios)

    judged_records: list[dict[str, Any]] = []
    predictions_path = out_dir / "predictions.jsonl"
    with predictions_path.open("w", encoding="utf-8") as predictions:
        for example_index, example in enumerate(examples):
            _, context_ids, _, suffix_ids, split_mode = prompt_parts(tokenizer, example)
            answers = answers_for(example)
            judge_mode = str(example.get("metadata", {}).get("utility_judge", "contains_any"))
            task = str(example.get("task", "unknown"))
            for method, keep_ratio in combinations:
                error = None
                try:
                    press = make_press(method, keep_ratio, [])
                    result = generate_one(
                        model=model,
                        tokenizer=tokenizer,
                        context_ids=context_ids,
                        suffix_ids=suffix_ids,
                        press=press,
                        max_new_tokens=args.max_new_tokens,
                        assistant_prefix_ids=[],
                        stop_after_json_object=False,
                        output_attentions=False,
                    )
                except Exception as exception:
                    error = repr(exception)
                    result = {
                        "output_text": "",
                        "generated_token_ids": [],
                        "generation_tokens": 0,
                        "prompt_tokens": len(context_ids) + len(suffix_ids),
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
                judged = judge_output(result["output_text"], answers, judge_mode)
                longbench_score = official_longbench_score(
                    task, result["output_text"], answers
                )
                record = {
                    "run_id": args.run_id,
                    "example_index": example_index,
                    "example_id": example["id"],
                    "task": task,
                    "source": example.get("source"),
                    "method": method,
                    "keep_ratio": keep_ratio,
                    "model": args.model,
                    "dataset": str(dataset_path),
                    "answers": answers,
                    "metadata": example.get("metadata", {}),
                    "prompt_split_mode": split_mode,
                    "error": error,
                    "longbench_score": longbench_score,
                    **judged,
                    **result,
                }
                judged_records.append(record)
                predictions.write(json.dumps(record, ensure_ascii=False) + "\n")
                predictions.flush()
                print(
                    json.dumps(
                        {
                            "example": example["id"],
                            "method": method,
                            "keep_ratio": keep_ratio,
                            "correct": judged["correct"],
                            "longbench_score": longbench_score,
                            "elapsed_seconds": result["elapsed_seconds"],
                            "error": error,
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )

    metrics = summarize(judged_records)
    metrics["errors"] = sum(record["error"] is not None for record in judged_records)
    metrics["num_rows"] = len(judged_records)
    write_json(out_dir / "metrics.json", metrics)
    run_config["end_time"] = now_iso()
    write_json(out_dir / "run_config.json", run_config)
    print(
        json.dumps(
            {
                "run_dir": str(out_dir),
                "prediction_rows": len(judged_records),
                "errors": metrics["errors"],
            },
            indent=2,
        )
    )
    if metrics["errors"]:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
