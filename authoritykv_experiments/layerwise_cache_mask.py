"""Decode-mask adapter for caches with layer-specific sequence lengths."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator

import torch


def adapt_attention_mask(
    attention_mask: torch.Tensor,
    *,
    past_length: int,
    query_length: int,
) -> torch.Tensor:
    """Align a shared mask to one layer's compressed cache length.

    The mask prefix addresses cached tokens and the final ``query_length``
    columns encode causal relations among the current forward call. Layer-wise
    compression changes only the prefix length, so the adapted mask keeps the
    matching prefix and the complete query tail.
    """

    if past_length < 0:
        raise ValueError("past_length must be non-negative")
    if query_length < 1:
        raise ValueError("query_length must be positive")
    target_length = past_length + query_length
    source_length = int(attention_mask.shape[-1])
    if source_length == target_length:
        return attention_mask
    if source_length < target_length:
        raise RuntimeError(
            "shared attention mask is shorter than the layer cache: "
            f"source={source_length} target={target_length}"
        )
    return torch.cat(
        (
            attention_mask[..., :past_length],
            attention_mask[..., -query_length:],
        ),
        dim=-1,
    )


@dataclass
class LayerwiseCacheMaskAdapter:
    """Temporarily align a shared decode mask to each cache layer."""

    activated: bool = False
    audit_records: list[dict[str, int]] = field(default_factory=list)

    @contextmanager
    def apply(self, model: Any, cache: Any) -> Generator[None, None, None]:
        lengths = [
            int(cache.get_seq_length(layer_index))
            for layer_index in range(len(cache))
        ]
        self.activated = len(set(lengths)) > 1
        if not self.activated:
            yield
            return

        language_model = (
            model.model.language_model
            if hasattr(model.model, "language_model")
            else model.model
        )
        hooks = []

        def align_mask(module, args, kwargs):
            mask = kwargs.get("attention_mask")
            hidden_states = kwargs.get("hidden_states")
            if mask is None or hidden_states is None:
                return args, kwargs
            query_length = int(hidden_states.shape[1])
            layer_index = int(module.layer_idx)
            past_length = int(cache.get_seq_length(layer_index))
            source_length = int(mask.shape[-1])
            target_length = past_length + query_length
            if source_length == target_length:
                return args, kwargs
            adjusted = adapt_attention_mask(
                mask,
                past_length=past_length,
                query_length=query_length,
            )
            updated = dict(kwargs)
            updated["attention_mask"] = adjusted
            self.audit_records.append(
                {
                    "layer": layer_index,
                    "past_length": past_length,
                    "query_length": query_length,
                    "source_mask_length": source_length,
                    "target_mask_length": target_length,
                }
            )
            return args, updated

        try:
            for layer in language_model.layers:
                hooks.append(
                    layer.self_attn.register_forward_pre_hook(
                        align_mask,
                        with_kwargs=True,
                    )
                )
            yield
        finally:
            for hook in hooks:
                hook.remove()
