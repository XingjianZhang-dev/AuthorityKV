#!/usr/bin/env python3
"""Run official KV presses with compact per-layer retention instrumentation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
for path in (str(SCRIPT_DIR), str(ROOT)):
    while path in sys.path:
        sys.path.remove(path)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SCRIPT_DIR))

from authoritykv_experiments import (  # noqa: E402
    InfeasibleBudgetError,
    build_official_press,
)
from authoritykv_experiments.retention_audit_press import (  # noqa: E402
    RetentionAuditPress,
)
from run_authoritykv_smoke import (  # noqa: E402
    detected_low_authority_token_set,
    find_token_spans,
    git_commit_or_null,
    span_token_set,
    untrusted_observation_token_set,
)
from run_kvpress_authority import (  # noqa: E402
    compact_span_summary,
    generate_one,
    prompt_parts,
)


VALID_METHODS = {
    "kvpress_snapkv",
    "kvpress_tova",
    "kvpress_pyramid",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument(
        "--methods",
        default="kvpress_snapkv,kvpress_tova,kvpress_pyramid",
    )
    parser.add_argument("--keep-ratios", default="0.2,0.4")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--max-new-tokens", type=int, default=16)
    parser.add_argument("--assistant-prefix", default='{"decision":"')
    parser.add_argument("--stop-after-json-object", action="store_true")
    parser.add_argument("--dtype", choices=["bf16", "fp16"], default="bf16")
    parser.add_argument(
        "--experiment-config",
        default="configs/acl_main_outcome_informed_followup.json",
    )
    parser.add_argument("--out-dir", required=True)
    return parser.parse_args()


def csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def float_csv(value: str) -> list[float]:
    return [float(part.strip()) for part in value.split(",") if part.strip()]


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n"
        )
        handle.flush()


def token_groups(token_spans: list[dict[str, Any]]) -> dict[str, list[int]]:
    return {
        "system": sorted(span_token_set(token_spans, {"system"})),
        "developer": sorted(span_token_set(token_spans, {"developer"})),
        "high_authority": sorted(
            span_token_set(token_spans, {"system", "developer"})
        ),
        "typed_low_authority": sorted(
            span_token_set(
                token_spans,
                {"user", "tool", "retrieved_document"},
            )
        ),
        "detected_low_authority": sorted(
            detected_low_authority_token_set(
                token_spans,
                detector_version="v3",
            )
        ),
        "provenance_untrusted": sorted(
            untrusted_observation_token_set(token_spans)
        ),
    }


def main() -> None:
    args = parse_args()
    methods = csv(args.methods)
    unknown = sorted(set(methods) - VALID_METHODS)
    if unknown:
        raise SystemExit(f"unsupported diagnostic methods: {unknown}")
    keep_ratios = float_csv(args.keep_ratios)
    if any(not 0 < ratio < 1 for ratio in keep_ratios):
        raise SystemExit("keep ratios must be in (0, 1)")
    if not torch.cuda.is_available():
        raise SystemExit("CUDA is required")

    import kvpress
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer

    torch.manual_seed(20260530)
    torch.cuda.manual_seed_all(20260530)
    torch.backends.cuda.matmul.allow_tf32 = True

    dataset_path = Path(args.dataset)
    rows = [
        json.loads(line)
        for line in dataset_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ][: args.limit]
    if not rows:
        raise SystemExit("diagnostic dataset is empty")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = out_dir / "predictions.jsonl"
    if predictions_path.exists():
        predictions_path.unlink()

    dtype = {
        "bf16": torch.bfloat16,
        "fp16": torch.float16,
    }[args.dtype]
    tokenizer = AutoTokenizer.from_pretrained(args.model, use_fast=True)
    if tokenizer.pad_token_id is None and tokenizer.eos_token_id is not None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        dtype=dtype,
        device_map={"": 0},
    )
    model.eval()

    config_path = Path(args.experiment_config)
    if not config_path.is_absolute():
        config_path = ROOT / config_path
    kvpress_root = ROOT / "external" / "kvpress"
    if not kvpress_root.exists():
        kvpress_root = ROOT / "external" / "kvpress_upstream"
    source_paths = [
        Path(__file__).resolve(),
        ROOT / "authoritykv_experiments" / "retention_audit_press.py",
        ROOT / "scripts" / "run_kvpress_authority.py",
        ROOT / "authoritykv_experiments" / "kvpress_authority.py",
    ]
    run_config = {
        "run_id": args.run_id,
        "start_time": now(),
        "command": " ".join(shlex.quote(part) for part in sys.argv),
        "model": args.model,
        "model_class": type(model).__name__,
        "model_commit": getattr(model.config, "_commit_hash", None),
        "num_hidden_layers": int(model.config.num_hidden_layers),
        "tokenizer_class": type(tokenizer).__name__,
        "dataset": str(dataset_path),
        "dataset_sha256": sha256(dataset_path),
        "limit": args.limit,
        "methods": methods,
        "keep_ratios": keep_ratios,
        "max_new_tokens": args.max_new_tokens,
        "assistant_prefix": args.assistant_prefix,
        "stop_after_json_object": args.stop_after_json_object,
        "dtype": args.dtype,
        "prefill_protocol": "one_shot_official_kvpress_instrumented",
        "instrumentation_equivalence": (
            "Delegate official score computation and reproduce the upstream "
            "top-k/layer-budget gather exactly; log masks after selection."
        ),
        "gpu": torch.cuda.get_device_name(0),
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
        "kvpress_version": getattr(kvpress, "__version__", "not_exposed"),
        "kvpress_commit": git_commit_or_null(kvpress_root),
        "experiment_config": str(config_path),
        "experiment_config_sha256": (
            sha256(config_path) if config_path.exists() else None
        ),
        "source_hashes": {
            str(path.relative_to(ROOT)): sha256(path)
            for path in source_paths
        },
    }
    write_json(out_dir / "run_config.json", run_config)

    prefix_ids = [
        int(token)
        for token in tokenizer(
            args.assistant_prefix,
            add_special_tokens=False,
        )["input_ids"]
    ]
    for example_index, example in enumerate(rows):
        context_text, context_ids, offsets, suffix_ids, split_mode = (
            prompt_parts(tokenizer, example)
        )
        spans = find_token_spans(
            context_text,
            offsets,
            example,
            span_source="metadata",
        )
        groups = token_groups(spans)
        for method in methods:
            for keep_ratio in keep_ratios:
                status = "ok"
                error = None
                infeasible_reason = None
                try:
                    press = RetentionAuditPress(
                        base_press=build_official_press(
                            method,
                            1.0 - keep_ratio,
                        ),
                        compression_ratio=1.0 - keep_ratio,
                        token_groups=groups,
                    )
                    result = generate_one(
                        model=model,
                        tokenizer=tokenizer,
                        context_ids=context_ids,
                        suffix_ids=suffix_ids,
                        press=press,
                        max_new_tokens=args.max_new_tokens,
                        assistant_prefix_ids=prefix_ids,
                        stop_after_json_object=args.stop_after_json_object,
                        output_attentions=False,
                    )
                except InfeasibleBudgetError as exc:
                    status = "infeasible"
                    infeasible_reason = str(exc)
                    result = {}
                except Exception as exc:
                    status = "runtime_error"
                    error = repr(exc)
                    result = {}
                record = {
                    "run_id": args.run_id,
                    "example_index": example_index,
                    "example_id": example["id"],
                    "category": example.get("category"),
                    "model": args.model,
                    "dataset": str(dataset_path),
                    "method": method,
                    "keep_ratio": keep_ratio,
                    "status": status,
                    "error": error,
                    "infeasible_reason": infeasible_reason,
                    "output_text": result.get("output_text", ""),
                    "generated_token_ids": result.get(
                        "generated_token_ids",
                        [],
                    ),
                    "generation_tokens": result.get(
                        "generation_tokens"
                    ),
                    "max_new_tokens": args.max_new_tokens,
                    "prompt_tokens": result.get("prompt_tokens"),
                    "retained_prompt_tokens": result.get(
                        "retained_prompt_tokens"
                    ),
                    "prefill_seconds": result.get("prefill_seconds"),
                    "decode_seconds": result.get("decode_seconds"),
                    "elapsed_seconds": result.get("elapsed_seconds"),
                    "peak_memory_mb": result.get("peak_memory_mb"),
                    "press_audit": result.get("press_audit", []),
                    "prompt_split_mode": split_mode,
                    "authority_token_spans": compact_span_summary(spans),
                    "expected_behavior": example.get("expected_behavior"),
                    "judge_rule": example.get("judge_rule"),
                    "metadata": example.get("metadata"),
                }
                append_jsonl(predictions_path, record)

    run_config["end_time"] = now()
    write_json(out_dir / "run_config.json", run_config)
    generation_metrics = {
        "schema_version": "2.0",
        "source": "retention_diagnostic_runner",
        "run_id": args.run_id,
        "rows": len(rows) * len(methods) * len(keep_ratios),
        "runtime_errors": sum(
            json.loads(line).get("status") == "runtime_error"
            for line in predictions_path.read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip()
        ),
        "end_time": run_config["end_time"],
        "predictions_sha256": sha256(predictions_path),
        "run_config_sha256": sha256(out_dir / "run_config.json"),
    }
    # The generic behavioral judge owns metrics.json. Keep generation
    # provenance in a separate file so judging cannot overwrite it.
    write_json(out_dir / "generation_metrics.json", generation_metrics)
    write_json(out_dir / "metrics.json", generation_metrics)
    print(
        json.dumps(
            {
                "run_dir": str(out_dir),
                "rows": len(rows) * len(methods) * len(keep_ratios),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
