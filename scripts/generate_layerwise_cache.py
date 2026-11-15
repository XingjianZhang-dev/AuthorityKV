"""Outcome-only generation for heterogeneous per-layer KV cache lengths."""

from __future__ import annotations

import contextlib
import time
from statistics import mean
from typing import Any

import torch

from authoritykv_experiments.layerwise_cache_mask import (
    LayerwiseCacheMaskAdapter,
)
from run_kvpress_authority import (
    cache_lengths,
    closed_first_json_object,
)


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
    layerwise_mask_adapter: bool = True,
) -> dict[str, Any]:
    """Generate with an outcome-only per-layer decode-mask adapter."""

    from transformers import DynamicCache

    device = model.device
    context_tensor = torch.tensor(
        [context_ids],
        dtype=torch.long,
        device=device,
    )
    suffix_tensor = torch.tensor(
        [suffix_ids],
        dtype=torch.long,
        device=device,
    )
    original_context_length = int(context_tensor.shape[1])
    prompt_length = original_context_length + int(suffix_tensor.shape[1])

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats(device)
    torch.cuda.synchronize(device)
    total_started = time.perf_counter()

    cache = DynamicCache()
    prefill_started = time.perf_counter()
    press_context = (
        press(model) if press is not None else contextlib.nullcontext()
    )
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
    mask_adapter = LayerwiseCacheMaskAdapter()
    decode_context = (
        mask_adapter.apply(model, cache)
        if layerwise_mask_adapter
        else contextlib.nullcontext()
    )
    with decode_context:
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
            forced_tensor = torch.tensor(
                [[forced_id]],
                dtype=torch.long,
                device=device,
            )
            outputs = model(
                input_ids=forced_tensor,
                past_key_values=cache,
                position_ids=torch.tensor(
                    [[position]],
                    dtype=torch.long,
                    device=device,
                ),
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
            partial_text = tokenizer.decode(
                generated_ids,
                skip_special_tokens=True,
            )
            if (
                stop_after_json_object
                and closed_first_json_object(partial_text)
            ):
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
            next_token = outputs.logits[:, -1, :].argmax(
                dim=-1,
                keepdim=True,
            )

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
        "layerwise_mask_adapter_activated": mask_adapter.activated,
        "layerwise_mask_adapter_audit": mask_adapter.audit_records,
    }
