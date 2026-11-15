#!/usr/bin/env python3
"""Run official KVPress methods on adapted OpenAI IH-Challenge examples."""

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
# Reinsert both entries deterministically. Adding the repository root ahead
# of an already-present scripts directory would import the stale root-level
# module instead of the frozen runner under scripts/.
for search_path in (str(ROOT), str(SCRIPTS)):
    while search_path in sys.path:
        sys.path.remove(search_path)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SCRIPTS))

from run_authoritykv_smoke import find_token_spans  # noqa: E402
from run_ih_challenge_kv import (  # noqa: E402
    injection_followed,
    official_grade,
    summarize,
)
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
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-new-tokens", type=int, default=16)
    parser.add_argument("--seed", type=int, default=20260530)
    parser.add_argument("--dtype", choices=["bf16", "fp16", "fp32"], default="bf16")
    parser.add_argument("--attn-implementation", default=None)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument(
        "--experiment-config",
        default="configs/acl_main_experiment_matrix.json",
    )
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def role_compatible_example(
    tokenizer: Any,
    example: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    """Fail closed when a model chat template silently drops control roles.

    Some open-weight templates accept a ``developer`` message syntactically but
    omit it from the rendered prompt. If every original message is preserved,
    the native template is used. Otherwise, only missing system/developer roles
    may be repaired: their exact contents are serialized, with explicit role
    boundaries, into one system message. Missing user/tool/assistant contents
    are a protocol error because silently changing those roles would alter the
    task.
    """

    messages = example.get("messages", [])
    if not messages or not getattr(tokenizer, "chat_template", None):
        return example, "raw_or_no_chat_template"
    native_error: Exception | None = None
    try:
        native_text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=False,
        )
    except Exception as exception:
        native_error = exception
        native_text = ""
    if native_error is not None:
        missing = [
            message
            for message in messages
            if str(message.get("role", "")).lower() in {"system", "developer"}
        ]
    else:
        missing = [
            message
            for message in messages
            if str(message.get("content", ""))
            and str(message.get("content", "")) not in native_text
        ]
    if not missing:
        return example, "native_roles"
    unsupported_missing = [
        message
        for message in missing
        if str(message.get("role", "")).lower() not in {"system", "developer"}
    ]
    if unsupported_missing:
        roles = sorted(
            {str(message.get("role", "")) for message in unsupported_missing}
        )
        raise RuntimeError(
            "chat template dropped non-control message role(s): "
            + ", ".join(roles)
        )

    control_messages = [
        message
        for message in messages
        if str(message.get("role", "")).lower() in {"system", "developer"}
    ]
    if native_error is not None and not control_messages:
        raise RuntimeError(
            "native chat template failed and there is no control role to "
            "serialize"
        ) from native_error
    other_messages = [
        message
        for message in messages
        if str(message.get("role", "")).lower() not in {"system", "developer"}
    ]
    control_chunks = [
        "The following control messages retain their original authority labels.",
    ]
    for index, message in enumerate(control_messages):
        role = str(message.get("role", "")).upper()
        content = str(message.get("content", ""))
        control_chunks.extend(
            [
                f"BEGIN ORIGINAL {role} MESSAGE [{index}]",
                content,
                f"END ORIGINAL {role} MESSAGE [{index}]",
            ]
        )
    adapted = {
        **example,
        "messages": [
            {"role": "system", "content": "\n".join(control_chunks)},
            *other_messages,
        ],
    }
    try:
        adapted_text = tokenizer.apply_chat_template(
            adapted["messages"],
            tokenize=False,
            add_generation_prompt=False,
        )
    except Exception as exception:
        raise RuntimeError(
            "role-compatible chat rendering failed after control-role "
            "serialization"
        ) from exception
    still_missing = [
        str(message.get("role", ""))
        for message in messages
        if str(message.get("content", ""))
        and str(message.get("content", "")) not in adapted_text
    ]
    if still_missing:
        raise RuntimeError(
            "role-compatible rendering still dropped message content: "
            + ", ".join(still_missing)
        )
    mode = "control_roles_serialized_in_system_channel"
    if native_error is not None:
        mode += "_after_native_template_error"
    return adapted, mode


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
    if attention_methods and set(methods) - ATTENTION_OUTPUT_METHODS:
        raise SystemExit("run H2O/ObservedAttention methods separately")

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
    attention_implementation = args.attn_implementation
    if attention_implementation is None and attention_methods:
        attention_implementation = "eager"
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
        ROOT / "scripts/run_kvpress_ih_challenge.py",
        ROOT / "scripts/run_kvpress_authority.py",
        ROOT / "scripts/run_ih_challenge_kv.py",
        ROOT / "scripts/make_ih_challenge_subset.py",
        ROOT / "scripts/remap_ih_control_role.py",
        ROOT / "authoritykv_experiments/kvpress_authority.py",
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
        "experiment_config_sha256": (
            file_sha256(experiment_config) if experiment_config.exists() else None
        ),
        "kvpress_commit": git_revision(kvpress_root),
        "model": args.model,
        "model_class": type(model).__name__,
        "model_commit": getattr(model.config, "_commit_hash", None),
        "model_max_position_embeddings": getattr(
            model.config,
            "max_position_embeddings",
            None,
        ),
        "tokenizer_class": type(tokenizer).__name__,
        "tokenizer_commit": getattr(tokenizer, "init_kwargs", {}).get(
            "_commit_hash"
        ),
        "dataset": str(dataset_path),
        "dataset_sha256": file_sha256(dataset_path),
        "dataset_rows": len(examples),
        "methods": methods,
        "keep_ratios": keep_ratios,
        "max_new_tokens": args.max_new_tokens,
        "seed": args.seed,
        "dtype": args.dtype,
        "attn_implementation": attention_implementation,
        "span_protocol": "actual_high_authority_chat_roles_plus_typed_metadata_spans",
        "role_compatibility_protocol": (
            "native role rendering when lossless; otherwise exact system/developer "
            "contents are boundary-tagged and serialized in the system channel; "
            "all other dropped roles fail closed"
        ),
        "gpu": torch.cuda.get_device_name(0),
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

    records: list[dict[str, Any]] = []
    with (out_dir / "predictions.jsonl").open("w", encoding="utf-8") as handle:
        for example_index, example in enumerate(examples):
            prompt_example, role_compatibility_mode = role_compatible_example(
                tokenizer,
                example,
            )
            context_text, context_ids, offsets, suffix_ids, split_mode = prompt_parts(
                tokenizer, prompt_example
            )
            token_spans = find_token_spans(
                context_text, offsets, example, span_source="metadata"
            )
            span_summary = compact_span_summary(token_spans)
            for method, keep_ratio in combinations:
                error = None
                status = "ok"
                infeasible_reason = None
                try:
                    press = make_press(method, keep_ratio, token_spans)
                    result = generate_one(
                        model=model,
                        tokenizer=tokenizer,
                        context_ids=context_ids,
                        suffix_ids=suffix_ids,
                        press=press,
                        max_new_tokens=args.max_new_tokens,
                        assistant_prefix_ids=[],
                        stop_after_json_object=False,
                        output_attentions=method in ATTENTION_OUTPUT_METHODS,
                    )
                except InfeasibleBudgetError as exception:
                    status = "infeasible"
                    infeasible_reason = str(exception)
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
                except Exception as exception:
                    error = repr(exception)
                    status = "runtime_error"
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
                official_correct, grader_error = official_grade(
                    example, result["output_text"]
                )
                record = {
                    "run_id": args.run_id,
                    "example_index": example_index,
                    "example_id": example["id"],
                    "category": example.get("category"),
                    "task_type": example.get("metadata", {}).get("task_type"),
                    "expected_city": example.get("metadata", {}).get("expected_city"),
                    "method": method,
                    "keep_ratio": keep_ratio,
                    "model": args.model,
                    "dataset": str(dataset_path),
                    "prompt_split_mode": split_mode,
                    "role_compatibility_mode": role_compatibility_mode,
                    "authority_token_spans": span_summary,
                    "status": status,
                    "error": error,
                    "infeasible_reason": infeasible_reason,
                    "grader_error": grader_error,
                    "official_correct": official_correct,
                    "injection_followed": injection_followed(result["output_text"]),
                    **result,
                }
                records.append(record)
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                handle.flush()
                print(
                    json.dumps(
                        {
                            "example": example["id"],
                            "method": method,
                            "keep_ratio": keep_ratio,
                            "official_correct": official_correct,
                            "injection_followed": record["injection_followed"],
                            "status": status,
                            "error": error,
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )

    metrics = summarize(records)
    metrics["runtime_errors"] = sum(
        record.get("status") == "runtime_error" for record in records
    )
    metrics["grader_errors"] = sum(
        record.get("grader_error") is not None for record in records
    )
    metrics["infeasible"] = sum(
        record.get("status") == "infeasible" for record in records
    )
    metrics["num_rows"] = len(records)
    write_json(out_dir / "metrics.json", metrics)
    run_config["end_time"] = now_iso()
    write_json(out_dir / "run_config.json", run_config)
    print(json.dumps({"run_dir": str(out_dir), "rows": len(records)}, indent=2))


if __name__ == "__main__":
    main()
