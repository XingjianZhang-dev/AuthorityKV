#!/usr/bin/env python3
"""Run official KVPress baselines and AuthorityKV in one common harness."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import random
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from authoritykv_experiments import (  # noqa: E402
    AuthorityAwarePress,
    InfeasibleBudgetError,
    OFFICIAL_PRESS_METHODS,
    build_official_press,
)
from run_authoritykv_smoke import (  # noqa: E402
    detected_low_authority_token_set,
    find_token_spans,
    span_token_set,
    untrusted_observation_token_set,
)


COMPOSED_BASES = {
    "snapkv": "kvpress_snapkv",
    "streaming": "kvpress_streaming",
    "knorm": "kvpress_knorm",
    "h2o": "kvpress_h2o",
}
COMPOSED_VARIANTS = {
    "system_pin": ("system", "pin"),
    "all_control_pin": ("all_control", "pin"),
    "authority_pin": ("authority", "pin"),
    "authority_detected": ("authority", "detected"),
    "authority_provenance": ("authority", "provenance"),
    "authority_detected_provenance": ("authority", "detected_provenance"),
}
COMPOSED_METHODS = {
    f"{prefix}_{base}_{suffix}"
    for base in COMPOSED_BASES
    for prefix, suffix in COMPOSED_VARIANTS.values()
}
AUTHORITY_METHODS = COMPOSED_METHODS
VALID_METHODS = {"fullkv", *OFFICIAL_PRESS_METHODS, *AUTHORITY_METHODS}
ATTENTION_OUTPUT_METHODS = {
    "kvpress_h2o",
    *(method for method in COMPOSED_METHODS if "_h2o_" in method),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--methods", required=True, help="Comma-separated method names.")
    parser.add_argument("--keep-ratios", default="0.20,0.40")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-new-tokens", type=int, default=32)
    parser.add_argument("--seed", type=int, default=20260530)
    parser.add_argument("--dtype", choices=["bf16", "fp16", "fp32"], default="bf16")
    parser.add_argument("--attn-implementation", default=None)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument(
        "--experiment-config",
        default="configs/acl_main_experiment_matrix.json",
        help="Optional frozen experiment-matrix JSON recorded with the run.",
    )
    parser.add_argument(
        "--span-source",
        choices=["metadata", "inferred", "metadata_plus_inferred"],
        default="metadata",
    )
    parser.add_argument(
        "--protected-budget-policy",
        choices=["strict", "priority"],
        default="strict",
        help=(
            "strict requires every protected token to fit. priority preserves the "
            "P>E>D ordering when the protected tier itself exceeds the budget, so "
            "the base scorer selects within P while no lower tier can displace it."
        ),
    )
    parser.add_argument(
        "--metadata-span-drop-rate",
        type=float,
        default=0.0,
        help=(
            "Deterministically drop this fraction of metadata-provided low-authority "
            "spans before cache selection. Chat-role spans are never dropped."
        ),
    )
    parser.add_argument(
        "--metadata-span-boundary-shrink-tokens",
        type=int,
        default=0,
        help=(
            "Remove this many tokens from each boundary of every metadata-provided "
            "low-authority span before cache selection."
        ),
    )
    parser.add_argument(
        "--scan-low-authority-chat",
        action="store_true",
        help=(
            "Scan user/tool chat content for detector triggers. Triggering text is "
            "localized to sentence/line spans so useful evidence in the same "
            "message is not demoted wholesale."
        ),
    )
    parser.add_argument("--assistant-prefix", default="")
    parser.add_argument("--stop-after-json-object", action="store_true")
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def parse_float_csv(value: str) -> list[float]:
    return [float(part.strip()) for part in value.split(",") if part.strip()]


def load_jsonl(path: Path, limit: int | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
            if limit is not None and len(rows) >= limit:
                break
    return rows


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def git_revision(path: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=path,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return None


def source_digest(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(str(path.relative_to(ROOT)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def longest_common_prefix(left: list[int], right: list[int]) -> int:
    length = 0
    for left_id, right_id in zip(left, right):
        if left_id != right_id:
            break
        length += 1
    return length


def prompt_parts(
    tokenizer: Any,
    example: dict[str, Any],
) -> tuple[str, list[int], list[tuple[int, int]], list[int], str]:
    """Return compressed context text/ids/offsets and uncompressed suffix ids."""

    messages = example.get("messages")
    if messages and getattr(tokenizer, "chat_template", None):
        context_text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=False,
        )
        full_text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        context_encoded = tokenizer(
            context_text,
            add_special_tokens=False,
            return_offsets_mapping=True,
        )
        full_ids = [
            int(token)
            for token in tokenizer(full_text, add_special_tokens=False)["input_ids"]
        ]
        context_ids = [int(token) for token in context_encoded["input_ids"]]
        prefix_length = longest_common_prefix(context_ids, full_ids)
        if prefix_length == len(context_ids) and prefix_length < len(full_ids):
            suffix_ids = full_ids[prefix_length:]
            split_mode = "chat_generation_suffix"
        else:
            # Fail closed to a token-prefix split if the tokenizer's template is
            # not text-prefix stable.
            if prefix_length < 1:
                raise RuntimeError("chat template has no stable token prefix")
            context_ids = full_ids[:prefix_length]
            suffix_ids = full_ids[prefix_length:]
            split_mode = "chat_token_lcp"
        offsets = [tuple(pair) for pair in context_encoded["offset_mapping"][: len(context_ids)]]
        if not suffix_ids:
            suffix_ids = [context_ids.pop()]
            offsets = offsets[: len(context_ids)]
            split_mode += "_last_token_fallback"
        return context_text, context_ids, offsets, suffix_ids, split_mode

    prompt = str(example.get("prompt") or example.get("context") or "")
    if not prompt:
        raise RuntimeError("example contains neither messages, prompt, nor context")
    encoded = tokenizer(
        prompt,
        add_special_tokens=False,
        return_offsets_mapping=True,
    )
    full_ids = [int(token) for token in encoded["input_ids"]]
    if len(full_ids) < 2:
        raise RuntimeError("prompt must contain at least two tokens")
    return (
        prompt,
        full_ids[:-1],
        [tuple(pair) for pair in encoded["offset_mapping"][:-1]],
        full_ids[-1:],
        "raw_last_token_suffix",
    )


def compact_span_summary(token_spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries = []
    for span in token_spans:
        token_indices = [int(index) for index in span.get("token_indices", [])]
        summaries.append(
            {
                "level": span.get("level"),
                "span_id": span.get("span_id"),
                "source": span.get("source"),
                "token_count": len(token_indices),
                "token_start": min(token_indices) if token_indices else None,
                "token_end": max(token_indices) if token_indices else None,
            }
        )
    return summaries


def perturb_metadata_spans(
    token_spans: list[dict[str, Any]],
    *,
    example_id: str,
    seed: int,
    drop_rate: float,
    boundary_shrink_tokens: int,
) -> list[dict[str, Any]]:
    """Apply frozen, outcome-independent metadata noise for robustness sweeps."""

    if not 0.0 <= drop_rate <= 1.0:
        raise ValueError("metadata span drop rate must be in [0, 1]")
    if boundary_shrink_tokens < 0:
        raise ValueError("metadata span boundary shrink must be non-negative")

    perturbed: list[dict[str, Any]] = []
    for span in token_spans:
        updated = dict(span)
        is_noisable = (
            updated.get("source") == "metadata_marker"
            and updated.get("level") not in {"system", "developer"}
        )
        if is_noisable and drop_rate:
            key = (
                f"{seed}\0{example_id}\0{updated.get('span_id', '')}"
            ).encode("utf-8")
            draw = int.from_bytes(hashlib.sha256(key).digest()[:8], "big") / 2**64
            if draw < drop_rate:
                continue
        if is_noisable and boundary_shrink_tokens:
            indices = [int(index) for index in updated.get("token_indices", [])]
            shrink = min(boundary_shrink_tokens, len(indices) // 2)
            updated["token_indices"] = (
                indices[shrink : len(indices) - shrink] if shrink else indices
            )
            updated["boundary_shrink_tokens"] = shrink
        perturbed.append(updated)
    return perturbed


def make_press(
    method: str,
    keep_ratio: float,
    token_spans: list[dict[str, Any]],
    *,
    strict_protected_budget: bool = True,
):
    if method == "fullkv":
        return None
    compression_ratio = 1.0 - keep_ratio
    if method in OFFICIAL_PRESS_METHODS:
        return build_official_press(method, compression_ratio)

    base_name = next(
        (candidate for candidate in COMPOSED_BASES if f"_{candidate}_" in method),
        None,
    )
    if base_name is None:
        raise ValueError(f"unable to resolve composed base press for method: {method}")
    if method.startswith("system_"):
        protected_levels = {"system"}
    elif method.startswith("all_control_"):
        protected_levels = {
            "system",
            "developer",
            "user",
            "tool",
            "retrieved_document",
        }
    else:
        protected_levels = {"system", "developer"}
    protected = span_token_set(token_spans, protected_levels)
    # Detector-only evidence must come from the model-visible chat text rather
    # than metadata-provided authority spans. Otherwise the detector silently
    # consumes the provenance signal that the robustness sweep is intended to
    # remove, confounding detector coverage with metadata availability.
    detector_spans = [
        span for span in token_spans if span.get("source") == "chat_message"
    ]
    detected = detected_low_authority_token_set(
        detector_spans,
        detector_version="v3",
    )
    provenance = untrusted_observation_token_set(token_spans)
    excluded: set[int] = set()
    if method.endswith("_detected") or method.endswith("_detected_provenance"):
        excluded.update(detected)
    if method.endswith("_provenance"):
        excluded.update(provenance)

    return AuthorityAwarePress(
        base_press=build_official_press(COMPOSED_BASES[base_name], compression_ratio),
        compression_ratio=compression_ratio,
        protected_token_indices=tuple(sorted(protected)),
        excluded_token_indices=tuple(sorted(excluded)),
        strict_protected_budget=strict_protected_budget,
    )


def cache_lengths(cache: Any) -> list[int]:
    return [int(cache.get_seq_length(layer_index)) for layer_index in range(len(cache))]


def closed_first_json_object(text: str) -> bool:
    start = text.find("{")
    if start < 0:
        return False
    depth = 0
    in_string = False
    escaped = False
    for character in text[start:]:
        if escaped:
            escaped = False
            continue
        if character == "\\" and in_string:
            escaped = True
            continue
        if character == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return True
    return False


@torch.inference_mode()
def generate_one(
    model: Any,
    tokenizer: Any,
    context_ids: list[int],
    suffix_ids: list[int],
    press: Any,
    max_new_tokens: int,
    assistant_prefix_ids: list[int],
    stop_after_json_object: bool,
    output_attentions: bool,
) -> dict[str, Any]:
    from transformers import DynamicCache

    device = model.device
    context_tensor = torch.tensor([context_ids], dtype=torch.long, device=device)
    suffix_tensor = torch.tensor([suffix_ids], dtype=torch.long, device=device)
    original_context_length = int(context_tensor.shape[1])
    prompt_length = original_context_length + int(suffix_tensor.shape[1])

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats(device)
    torch.cuda.synchronize(device)
    total_started = time.perf_counter()

    cache = DynamicCache()
    prefill_started = time.perf_counter()
    press_context = press(model) if press is not None else contextlib.nullcontext()
    with press_context:
        model.model(
            input_ids=context_tensor,
            past_key_values=cache,
            use_cache=True,
            output_attentions=output_attentions,
        )
    torch.cuda.synchronize(device)
    prefill_seconds = time.perf_counter() - prefill_started
    retained_lengths = cache_lengths(cache)

    decode_started = time.perf_counter()
    suffix_position_ids = torch.arange(
        original_context_length,
        prompt_length,
        dtype=torch.long,
        device=device,
    ).unsqueeze(0)
    outputs = model(
        input_ids=suffix_tensor,
        past_key_values=cache,
        position_ids=suffix_position_ids,
        use_cache=True,
        return_dict=True,
        num_logits_to_keep=1,
    )

    generated_ids: list[int] = []
    eos_ids = model.generation_config.eos_token_id
    if not isinstance(eos_ids, list):
        eos_ids = [eos_ids]
    eos_set = {int(token) for token in eos_ids if token is not None}

    logits = outputs.logits
    for forced_id in assistant_prefix_ids[:max_new_tokens]:
        if forced_id in eos_set:
            break
        generated_ids.append(int(forced_id))
        position = prompt_length + len(generated_ids) - 1
        forced_tensor = torch.tensor([[forced_id]], dtype=torch.long, device=device)
        outputs = model(
            input_ids=forced_tensor,
            past_key_values=cache,
            position_ids=torch.tensor([[position]], dtype=torch.long, device=device),
            use_cache=True,
            return_dict=True,
            num_logits_to_keep=1,
        )
        logits = outputs.logits

    next_token = logits[:, -1, :].argmax(dim=-1, keepdim=True)
    for step in range(len(generated_ids), max_new_tokens):
        token_id = int(next_token.item())
        if token_id in eos_set:
            break
        generated_ids.append(token_id)
        partial_text = tokenizer.decode(generated_ids, skip_special_tokens=True)
        if stop_after_json_object and closed_first_json_object(partial_text):
            break
        outputs = model(
            input_ids=next_token,
            past_key_values=cache,
            position_ids=torch.tensor(
                [[prompt_length + step]],
                dtype=torch.long,
                device=device,
            ),
            use_cache=True,
            return_dict=True,
            num_logits_to_keep=1,
        )
        next_token = outputs.logits[:, -1, :].argmax(dim=-1, keepdim=True)

    torch.cuda.synchronize(device)
    decode_seconds = time.perf_counter() - decode_started
    total_seconds = time.perf_counter() - total_started
    peak_memory_mb = torch.cuda.max_memory_allocated(device) / (1024**2)

    return {
        "output_text": tokenizer.decode(
            generated_ids,
            skip_special_tokens=True,
        ).strip(),
        "generated_token_ids": generated_ids,
        "generation_tokens": len(generated_ids),
        "prompt_tokens": prompt_length,
        "retained_prompt_tokens": round(mean(retained_lengths), 3),
        "retained_prompt_tokens_min": min(retained_lengths),
        "retained_prompt_tokens_max": max(retained_lengths),
        "prefill_seconds": round(prefill_seconds, 6),
        "decode_seconds": round(decode_seconds, 6),
        "elapsed_seconds": round(total_seconds, 6),
        "decode_tokens_per_second": round(
            len(generated_ids) / decode_seconds if decode_seconds else 0.0,
            4,
        ),
        "peak_memory_mb": round(peak_memory_mb, 3),
        "press_audit": getattr(press, "audit_records", []),
    }


def main() -> None:
    args = parse_args()
    methods = parse_csv(args.methods)
    unknown = sorted(set(methods) - VALID_METHODS)
    if unknown:
        raise SystemExit(f"unknown methods: {', '.join(unknown)}")
    keep_ratios = parse_float_csv(args.keep_ratios)
    if any(not 0 < ratio <= 1 for ratio in keep_ratios):
        raise SystemExit("keep ratios must be in (0, 1]")
    if not 0.0 <= args.metadata_span_drop_rate <= 1.0:
        raise SystemExit("metadata span drop rate must be in [0, 1]")
    if args.metadata_span_boundary_shrink_tokens < 0:
        raise SystemExit("metadata span boundary shrink must be non-negative")
    attention_methods = set(methods) & ATTENTION_OUTPUT_METHODS
    non_attention_methods = set(methods) - ATTENTION_OUTPUT_METHODS
    if attention_methods and non_attention_methods:
        raise SystemExit(
            "run H2O/ObservedAttention methods separately because they require eager attention"
        )

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    torch.backends.cuda.matmul.allow_tf32 = True

    from transformers import AutoModelForCausalLM, AutoTokenizer
    import transformers
    import kvpress

    dataset_path = Path(args.dataset)
    examples = load_jsonl(dataset_path, args.limit)
    if not examples:
        raise SystemExit("dataset is empty")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    attn_implementation = args.attn_implementation
    if attn_implementation is None and attention_methods:
        attn_implementation = "eager"
    dtype = {
        "bf16": torch.bfloat16,
        "fp16": torch.float16,
        "fp32": torch.float32,
    }[args.dtype]

    tokenizer = AutoTokenizer.from_pretrained(args.model, use_fast=True)
    if tokenizer.pad_token_id is None and tokenizer.eos_token_id is not None:
        tokenizer.pad_token = tokenizer.eos_token
    model_kwargs: dict[str, Any] = {
        "dtype": dtype,
        "device_map": {"": 0},
    }
    if attn_implementation:
        model_kwargs["attn_implementation"] = attn_implementation
    model = AutoModelForCausalLM.from_pretrained(args.model, **model_kwargs)
    model.eval()

    core_sources = [
        ROOT / "scripts/run_kvpress_authority.py",
        ROOT / "authoritykv_experiments/kvpress_authority.py",
        ROOT / "scripts/run_authoritykv_smoke.py",
        ROOT / "scripts/judge_authoritykv.py",
        ROOT / "scripts/run_acl_main_gpu_queue.sh",
    ]
    experiment_config_path = Path(args.experiment_config)
    if not experiment_config_path.is_absolute():
        experiment_config_path = ROOT / experiment_config_path
    experiment_config_sha256 = (
        file_sha256(experiment_config_path) if experiment_config_path.exists() else None
    )
    kvpress_root = ROOT / "external/kvpress"
    if not kvpress_root.exists():
        kvpress_root = ROOT / "external/kvpress_upstream"
    run_config = {
        "run_id": args.run_id,
        "start_time": now_iso(),
        "command": " ".join(shlex.quote(part) for part in sys.argv),
        "source_sha256": source_digest(core_sources),
        "source_hashes": {
            str(path.relative_to(ROOT)): file_sha256(path) for path in core_sources
        },
        "experiment_config": str(experiment_config_path.relative_to(ROOT))
        if experiment_config_path.exists()
        else args.experiment_config,
        "experiment_config_sha256": experiment_config_sha256,
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
        "tokenizer_commit": getattr(tokenizer, "init_kwargs", {}).get("_commit_hash"),
        "dataset": str(dataset_path),
        "dataset_sha256": file_sha256(dataset_path),
        "limit": args.limit,
        "methods": methods,
        "keep_ratios": keep_ratios,
        "max_new_tokens": args.max_new_tokens,
        "seed": args.seed,
        "dtype": args.dtype,
        "attn_implementation": attn_implementation,
        "span_source": args.span_source,
        "protected_budget_policy": args.protected_budget_policy,
        "metadata_span_drop_rate": args.metadata_span_drop_rate,
        "metadata_span_boundary_shrink_tokens": (
            args.metadata_span_boundary_shrink_tokens
        ),
        "scan_low_authority_chat": args.scan_low_authority_chat,
        "assistant_prefix": args.assistant_prefix,
        "stop_after_json_object": args.stop_after_json_object,
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

    assistant_prefix_ids = [
        int(token)
        for token in tokenizer(
            args.assistant_prefix,
            add_special_tokens=False,
        )["input_ids"]
    ]
    combinations = []
    for method in methods:
        if method == "fullkv":
            combinations.append((method, 1.0))
        else:
            combinations.extend((method, ratio) for ratio in keep_ratios)

    predictions_path = out_dir / "predictions.jsonl"
    with predictions_path.open("w", encoding="utf-8") as predictions:
        for example_index, example in enumerate(examples):
            (
                context_text,
                context_ids,
                offsets,
                suffix_ids,
                split_mode,
            ) = prompt_parts(tokenizer, example)
            token_spans = find_token_spans(
                context_text,
                offsets,
                example,
                span_source=args.span_source,
                include_low_authority_chat=args.scan_low_authority_chat,
            )
            token_spans = perturb_metadata_spans(
                token_spans,
                example_id=str(example["id"]),
                seed=args.seed,
                drop_rate=args.metadata_span_drop_rate,
                boundary_shrink_tokens=(
                    args.metadata_span_boundary_shrink_tokens
                ),
            )
            span_summary = compact_span_summary(token_spans)

            for method, keep_ratio in combinations:
                error = None
                status = "ok"
                infeasible_reason = None
                result: dict[str, Any]
                try:
                    press = make_press(
                        method,
                        keep_ratio,
                        token_spans,
                        strict_protected_budget=(
                            args.protected_budget_policy == "strict"
                        ),
                    )
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
                        "retained_prompt_tokens": 0,
                        "retained_prompt_tokens_min": 0,
                        "retained_prompt_tokens_max": 0,
                        "prefill_seconds": 0.0,
                        "decode_seconds": 0.0,
                        "elapsed_seconds": 0.0,
                        "decode_tokens_per_second": 0.0,
                        "peak_memory_mb": 0.0,
                        "press_audit": [],
                    }

                record = {
                    "run_id": args.run_id,
                    "example_index": example_index,
                    "example_id": example["id"],
                    "category": example.get("category", "external_utility"),
                    "method": method,
                    "keep_ratio": keep_ratio,
                    "model": args.model,
                    "dataset": str(dataset_path),
                    "max_new_tokens": args.max_new_tokens,
                    "seed": args.seed,
                    "protected_budget_policy": args.protected_budget_policy,
                    "scan_low_authority_chat": args.scan_low_authority_chat,
                    "metadata_span_drop_rate": args.metadata_span_drop_rate,
                    "metadata_span_boundary_shrink_tokens": (
                        args.metadata_span_boundary_shrink_tokens
                    ),
                    "status": status,
                    "error": error,
                    "infeasible_reason": infeasible_reason,
                    "expected_behavior": example.get("expected_behavior", {}),
                    "judge_rule": example.get("judge_rule", {}),
                    "metadata": example.get("metadata", {}),
                    "answers": example.get("answers"),
                    "prompt_split_mode": split_mode,
                    "authority_token_spans": span_summary,
                    **result,
                }
                predictions.write(json.dumps(record, ensure_ascii=False) + "\n")
                predictions.flush()
                print(
                    json.dumps(
                        {
                            "example": example["id"],
                            "method": method,
                            "keep_ratio": keep_ratio,
                            "prompt_tokens": result["prompt_tokens"],
                            "retained_min": result["retained_prompt_tokens_min"],
                            "retained_max": result["retained_prompt_tokens_max"],
                            "elapsed_seconds": result["elapsed_seconds"],
                            "status": status,
                            "error": error,
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )

    run_config["end_time"] = now_iso()
    write_json(out_dir / "run_config.json", run_config)
    print(json.dumps({"run_dir": str(out_dir), "predictions": str(predictions_path)}, indent=2))


if __name__ == "__main__":
    main()
