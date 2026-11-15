#!/usr/bin/env python3
"""Run isolated outcome-informed AuthorityKV stress and upgrade experiments."""

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
from authoritykv_experiments.outcome_informed_authority import (  # noqa: E402
    LayerBudgetAwareAuthorityPress,
)
from generate_layerwise_cache import generate_one  # noqa: E402
from run_authoritykv_smoke import (  # noqa: E402
    detected_low_authority_token_set,
    find_token_spans,
    git_commit_or_null,
    span_token_set,
    untrusted_observation_token_set,
)
from run_kvpress_authority import (  # noqa: E402
    compact_span_summary,
    prompt_parts,
)


BASES = ("snapkv", "tova", "pyramid")
OFFICIAL = {f"kvpress_{base}" for base in BASES}
V1 = {f"authority_{base}_v1" for base in BASES}
V2 = {f"authority_{base}_v2_adaptive" for base in BASES}
COUNTERFACTUAL = {
    f"counterfactual_{base}_v2_wrong_authority" for base in BASES
}
MATCHED_COUNTERFACTUAL = {
    f"counterfactual_{base}_v3_matched_wrong_authority"
    for base in BASES
}
VALID_METHODS = {
    "fullkv",
    *OFFICIAL,
    *V1,
    *V2,
    *COUNTERFACTUAL,
    *MATCHED_COUNTERFACTUAL,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--methods", required=True)
    parser.add_argument("--keep-ratios", default="0.1,0.2,0.4")
    parser.add_argument("--max-new-tokens", type=int, default=16)
    parser.add_argument("--assistant-prefix", default='{"decision":"')
    parser.add_argument("--stop-after-json-object", action="store_true")
    parser.add_argument("--dtype", choices=["bf16", "fp16"], default="bf16")
    parser.add_argument("--fullkv-run", default=None)
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


def source_digest(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(str(path.relative_to(ROOT)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


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


def authority_priority_sets(
    method: str,
    spans: list[dict[str, Any]],
) -> tuple[set[int], set[int]]:
    """Return protected and excluded token sets for an Authority method."""

    correct_protected = span_token_set(
        spans,
        {"system", "developer"},
    )
    correct_excluded = detected_low_authority_token_set(
        spans,
        detector_version="v3",
    )
    correct_excluded.update(untrusted_observation_token_set(spans))

    if method in COUNTERFACTUAL:
        protected = {
            int(index)
            for span in spans
            if "_low_" in str(span.get("span_id", ""))
            for index in span.get("token_indices", [])
        }
        excluded = {
            int(index)
            for span in spans
            if "_high_" in str(span.get("span_id", ""))
            for index in span.get("token_indices", [])
        }
    elif method in MATCHED_COUNTERFACTUAL:
        high_marker_tokens = {
            int(index)
            for span in spans
            if "_high_" in str(span.get("span_id", ""))
            for index in span.get("token_indices", [])
        }
        low_marker_tokens = {
            int(index)
            for span in spans
            if "_low_" in str(span.get("span_id", ""))
            for index in span.get("token_indices", [])
        }
        # Match the correct treatment everywhere except the registered
        # conflict spans. On benign examples both marker sets are empty,
        # making the two interventions exactly identical.
        protected = (correct_protected - high_marker_tokens) | (
            low_marker_tokens
        )
        excluded = (correct_excluded - low_marker_tokens) | (
            high_marker_tokens
        )
    else:
        protected = correct_protected
        excluded = correct_excluded

    excluded.difference_update(protected)
    return protected, excluded


def make_press(
    method: str,
    keep_ratio: float,
    spans: list[dict[str, Any]],
):
    if method == "fullkv":
        return None
    if method in OFFICIAL:
        return build_official_press(method, 1.0 - keep_ratio)
    base = next(
        (candidate for candidate in BASES if f"_{candidate}_" in method),
        None,
    )
    if base is None:
        raise ValueError(f"cannot resolve base press for {method}")
    protected, excluded = authority_priority_sets(method, spans)
    # The authority ordering is strict: a token cannot simultaneously receive
    # a protected and excluded priority. This also makes V2's over-subscribed
    # selection exactly the base-score-best subset of protected tokens.
    return LayerBudgetAwareAuthorityPress(
        base_press=build_official_press(
            f"kvpress_{base}",
            1.0 - keep_ratio,
        ),
        compression_ratio=1.0 - keep_ratio,
        protected_token_indices=tuple(sorted(protected)),
        excluded_token_indices=tuple(sorted(excluded)),
        strict_protected_budget=method in V1,
    )


def main() -> None:
    args = parse_args()
    methods = csv(args.methods)
    unknown = sorted(set(methods) - VALID_METHODS)
    if unknown:
        raise SystemExit(f"unknown outcome-informed methods: {unknown}")
    keep_ratios = float_csv(args.keep_ratios)
    if any(not 0 < ratio <= 1 for ratio in keep_ratios):
        raise SystemExit("keep ratios must be in (0, 1]")
    if not torch.cuda.is_available():
        raise SystemExit("CUDA is required")

    import kvpress
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer

    torch.manual_seed(20260530)
    torch.cuda.manual_seed_all(20260530)
    torch.backends.cuda.matmul.allow_tf32 = True

    dataset_path = Path(args.dataset)
    examples = [
        json.loads(line)
        for line in dataset_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not examples:
        raise SystemExit("outcome-informed dataset is empty")
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
        ROOT / "scripts" / "run_kvpress_authority.py",
        ROOT / "authoritykv_experiments" / "kvpress_authority.py",
        ROOT
        / "authoritykv_experiments"
        / "outcome_informed_authority.py",
        ROOT
        / "authoritykv_experiments"
        / "layerwise_cache_mask.py",
        ROOT / "scripts" / "generate_layerwise_cache.py",
        ROOT / "scripts" / "judge_authoritykv.py",
    ]
    run_config = {
        "run_id": args.run_id,
        "start_time": now(),
        "command": " ".join(shlex.quote(part) for part in sys.argv),
        "study_design": "outcome_informed_isolated_followup",
        "model": args.model,
        "model_class": type(model).__name__,
        "model_commit": getattr(model.config, "_commit_hash", None),
        "tokenizer_class": type(tokenizer).__name__,
        "dataset": str(dataset_path),
        "dataset_sha256": sha256(dataset_path),
        "examples": len(examples),
        "methods": methods,
        "keep_ratios": keep_ratios,
        "max_new_tokens": args.max_new_tokens,
        "assistant_prefix": args.assistant_prefix,
        "stop_after_json_object": args.stop_after_json_object,
        "fullkv_run": args.fullkv_run,
        "dtype": args.dtype,
        "prefill_protocol": "one_shot_official_kvpress",
        "v1_protocol": (
            "Strictly require all typed system/developer tokens to fit."
        ),
        "v2_protocol": (
            "Preserve the same lexicographic protected/excluded score offsets, "
            "but at an over-subscribed budget retain the base-score-best subset "
            "of protected tokens instead of declaring the cell infeasible."
        ),
        "counterfactual_protocol": (
            "On conflict examples only, invert the intervention by protecting "
            "the registered _low_ span and demoting the registered _high_ "
            "span. On benign examples the counterfactual reduces to the "
            "unmodified official scorer."
        ),
        "matched_counterfactual_protocol": (
            "Apply the same Authority V2 treatment to correct and control "
            "conditions everywhere, including benign examples, and invert "
            "only the registered _high_ and _low_ conflict spans in the "
            "matched wrong-authority control."
        ),
        "layer_budget_protocol": (
            "Use each base press's layer-specific budget when provided; "
            "otherwise use its fixed compression-ratio budget."
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
        "source_sha256": source_digest(source_paths),
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
    combinations_to_run: list[tuple[str, float]] = []
    for method in methods:
        if method == "fullkv":
            combinations_to_run.append((method, 1.0))
        else:
            combinations_to_run.extend(
                (method, ratio) for ratio in keep_ratios
            )
    for example_index, example in enumerate(examples):
        context_text, context_ids, offsets, suffix_ids, split_mode = (
            prompt_parts(tokenizer, example)
        )
        spans = find_token_spans(
            context_text,
            offsets,
            example,
            span_source="metadata",
        )
        for method, keep_ratio in combinations_to_run:
            status = "ok"
            error = None
            infeasible_reason = None
            try:
                press = make_press(method, keep_ratio, spans)
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
                "generation_tokens": result.get("generation_tokens"),
                "max_new_tokens": args.max_new_tokens,
                "prompt_tokens": result.get("prompt_tokens"),
                "retained_prompt_tokens": result.get(
                    "retained_prompt_tokens"
                ),
                "retained_prompt_tokens_min": result.get(
                    "retained_prompt_tokens_min"
                ),
                "retained_prompt_tokens_max": result.get(
                    "retained_prompt_tokens_max"
                ),
                "prefill_seconds": result.get("prefill_seconds"),
                "decode_seconds": result.get("decode_seconds"),
                "elapsed_seconds": result.get("elapsed_seconds"),
                "decode_tokens_per_second": result.get(
                    "decode_tokens_per_second"
                ),
                "peak_memory_mb": result.get("peak_memory_mb"),
                "press_audit": result.get("press_audit", []),
                "layerwise_mask_adapter_activated": result.get(
                    "layerwise_mask_adapter_activated",
                    False,
                ),
                "layerwise_mask_adapter_audit": result.get(
                    "layerwise_mask_adapter_audit",
                    [],
                ),
                "prompt_split_mode": split_mode,
                "authority_token_spans": compact_span_summary(spans),
                "expected_behavior": example.get("expected_behavior"),
                "judge_rule": example.get("judge_rule"),
                "metadata": example.get("metadata"),
            }
            append_jsonl(predictions_path, record)

    run_config["end_time"] = now()
    write_json(out_dir / "run_config.json", run_config)
    print(json.dumps({
        "run_dir": str(out_dir),
        "rows": len(examples) * len(combinations_to_run),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
