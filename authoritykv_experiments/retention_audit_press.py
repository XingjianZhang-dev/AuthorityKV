"""Outcome-informed instrumentation for official score-based KV presses."""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass, field
from typing import Mapping, Sequence

import torch
from torch import nn

from kvpress.presses.base_press import BasePress
from kvpress.presses.scorer_press import ScorerPress


def _packed_mask(mask: torch.Tensor) -> str:
    values = mask.detach().to(device="cpu", dtype=torch.bool).tolist()
    packed = bytearray((len(values) + 7) // 8)
    for index, selected in enumerate(values):
        if selected:
            packed[index // 8] |= 1 << (index % 8)
    return base64.b64encode(bytes(packed)).decode("ascii")


@dataclass
class RetentionAuditPress(BasePress):
    """Reproduce an official scorer press while logging compact selection masks.

    This wrapper is intentionally isolated from the frozen main implementation.
    It delegates score computation to the pinned upstream scorer, applies the
    same top-k rule and layer budget, and stores union/intersection masks across
    KV heads plus authority-span retention rates.
    """

    base_press: ScorerPress
    compression_ratio: float
    token_groups: Mapping[str, Sequence[int]] = field(default_factory=dict)
    audit_records: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.base_press, ScorerPress):
            raise TypeError("RetentionAuditPress requires a ScorerPress")
        if not 0 <= self.compression_ratio < 1:
            raise ValueError("compression_ratio must be in [0, 1)")
        self.base_press.compression_ratio = self.compression_ratio
        self.token_groups = {
            str(name): tuple(
                sorted({int(index) for index in indices if int(index) >= 0})
            )
            for name, indices in self.token_groups.items()
        }

    def post_init_from_model(self, model) -> None:
        self.base_press.post_init_from_model(model)

    def _kept_count(self, module: nn.Module, cache_length: int) -> int:
        layer_budget = getattr(self.base_press, "get_layer_budget", None)
        if callable(layer_budget):
            return int(layer_budget(module, cache_length))
        return max(1, int(cache_length * (1 - self.compression_ratio)))

    def compress(
        self,
        module: nn.Module,
        hidden_states: torch.Tensor,
        keys: torch.Tensor,
        values: torch.Tensor,
        attentions: torch.Tensor,
        kwargs: dict,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        if self.compression_ratio == 0:
            return keys, values
        scores = self.base_press.score(
            module,
            hidden_states,
            keys,
            values,
            attentions,
            kwargs,
        )
        cache_length = int(keys.shape[2])
        kept_count = self._kept_count(module, cache_length)
        kept_indices = scores.topk(kept_count, dim=-1).indices
        kept_mask = torch.zeros_like(scores, dtype=torch.bool)
        kept_mask.scatter_(-1, kept_indices, True)
        union_mask = kept_mask.any(dim=0).any(dim=0)
        intersection_mask = kept_mask.all(dim=0).all(dim=0)

        group_retention: dict[str, float | int] = {}
        for name, indices in self.token_groups.items():
            valid = [
                index for index in indices if 0 <= index < cache_length
            ]
            group_retention[f"{name}_count"] = len(valid)
            group_retention[f"{name}_kept_fraction"] = (
                float(
                    kept_mask.index_select(
                        -1,
                        torch.tensor(
                            valid,
                            dtype=torch.long,
                            device=kept_mask.device,
                        ),
                    )
                    .float()
                    .mean()
                    .item()
                )
                if valid
                else 0.0
            )

        sorted_indices = kept_indices.sort(dim=-1).values.detach().cpu()
        self.audit_records.append(
            {
                "layer": int(
                    getattr(module, "layer_idx", len(self.audit_records))
                ),
                "cache_length": cache_length,
                "kept_count": kept_count,
                "kv_head_count": int(kept_indices.shape[1]),
                "selection_union_count": int(union_mask.sum().item()),
                "selection_intersection_count": int(
                    intersection_mask.sum().item()
                ),
                "selection_union_b64_little_endian": _packed_mask(
                    union_mask
                ),
                "selection_intersection_b64_little_endian": _packed_mask(
                    intersection_mask
                ),
                "selection_indices_sha256": hashlib.sha256(
                    sorted_indices.numpy().tobytes()
                ).hexdigest(),
                "selected_position_fraction_mean": float(
                    kept_indices.float().mean().item()
                    / max(1, cache_length - 1)
                ),
                **group_retention,
            }
        )
        gather_indices = kept_indices.unsqueeze(-1).expand(
            -1,
            -1,
            -1,
            keys.shape[-1],
        )
        return (
            keys.gather(2, gather_indices).contiguous(),
            values.gather(2, gather_indices).contiguous(),
        )
