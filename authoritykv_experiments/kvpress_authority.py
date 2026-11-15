"""Authority-aware wrappers around the pinned NVIDIA KVPress implementations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import torch
from torch import nn

from kvpress import (
    KnormPress,
    ObservedAttentionPress,
    PyramidKVPress,
    SnapKVPress,
    StreamingLLMPress,
    TOVAPress,
)
from kvpress.presses.base_press import BasePress
from kvpress.presses.scorer_press import ScorerPress


OFFICIAL_PRESS_METHODS = {
    "kvpress_h2o",
    "kvpress_knorm",
    "kvpress_pyramid",
    "kvpress_snapkv",
    "kvpress_streaming",
    "kvpress_tova",
}


class InfeasibleBudgetError(RuntimeError):
    """The requested protected set cannot fit in the fixed KV budget."""


def build_official_press(method: str, compression_ratio: float) -> BasePress:
    """Construct a pinned upstream press from a stable paper-facing method name."""

    kwargs = {"compression_ratio": compression_ratio}
    if method == "kvpress_snapkv":
        return SnapKVPress(**kwargs)
    if method == "kvpress_h2o":
        return ObservedAttentionPress(**kwargs)
    if method == "kvpress_streaming":
        return StreamingLLMPress(**kwargs)
    if method == "kvpress_tova":
        return TOVAPress(**kwargs)
    if method == "kvpress_knorm":
        return KnormPress(**kwargs)
    if method == "kvpress_pyramid":
        return PyramidKVPress(**kwargs)
    raise ValueError(f"unknown official KVPress method: {method}")


@dataclass
class AuthorityAwarePress(BasePress):
    """Reserve high-authority tokens before filling the cache by a base scorer.

    The wrapper operates inside the same KVPress forward-hook implementation as
    the official score-based baselines. High-authority indices are guaranteed to
    survive whenever they fit inside the requested cache budget. Optionally,
    typed or detected untrusted spans are assigned the lowest priority, while
    still allowing a deterministic fallback if too few eligible tokens remain.
    """

    base_press: ScorerPress
    compression_ratio: float
    protected_token_indices: Sequence[int] = field(default_factory=tuple)
    excluded_token_indices: Sequence[int] = field(default_factory=tuple)
    strict_protected_budget: bool = True
    audit_records: list[dict[str, float | int]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.base_press, ScorerPress):
            raise TypeError("AuthorityAwarePress requires a score-based KVPress baseline")
        if not 0 <= self.compression_ratio < 1:
            raise ValueError("compression_ratio must be in [0, 1)")
        self.base_press.compression_ratio = self.compression_ratio
        protected = {
            int(index)
            for index in self.protected_token_indices
            if int(index) >= 0
        }
        self.protected_token_indices = tuple(sorted(protected))
        self.excluded_token_indices = tuple(
            sorted(
                {
                    int(index)
                    for index in self.excluded_token_indices
                    if int(index) >= 0 and int(index) not in protected
                }
            )
        )

    def post_init_from_model(self, model) -> None:
        self.base_press.post_init_from_model(model)

    @staticmethod
    def _valid_indices(indices: Sequence[int], length: int, device: torch.device) -> torch.Tensor:
        valid = [index for index in indices if index < length]
        return torch.tensor(valid, dtype=torch.long, device=device)

    @staticmethod
    def _canonicalize_base_scores(scores: torch.Tensor) -> torch.Tensor:
        """Map non-finite scorer sentinels to a bounded, order-safe range."""

        original = scores.float()
        finite_magnitude = torch.where(
            torch.isfinite(original),
            original.abs(),
            torch.zeros_like(original),
        ).amax(dim=-1, keepdim=True)
        sentinel = finite_magnitude + 1.0
        expanded = sentinel.expand_as(original)
        canonical = torch.where(torch.isnan(original), -expanded, original)
        canonical = torch.where(
            torch.isinf(canonical) & (canonical > 0),
            expanded,
            canonical,
        )
        canonical = torch.where(
            torch.isinf(canonical) & (canonical < 0),
            -expanded,
            canonical,
        )
        return canonical

    @classmethod
    def _priority_adjusted_scores(
        cls,
        scores: torch.Tensor,
        protected: torch.Tensor,
        excluded: torch.Tensor,
    ) -> torch.Tensor:
        adjusted = cls._canonicalize_base_scores(scores)
        magnitude = adjusted.abs().amax(dim=-1, keepdim=True)
        priority_offset = 4.0 * (magnitude + 1.0)

        if excluded.numel():
            adjusted.index_add_(
                -1,
                excluded,
                -priority_offset.expand(
                    *priority_offset.shape[:-1],
                    excluded.numel(),
                ),
            )
        if protected.numel():
            adjusted.index_add_(
                -1,
                protected,
                2.0
                * priority_offset.expand(
                    *priority_offset.shape[:-1],
                    protected.numel(),
                ),
            )
        return adjusted

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
        if scores.ndim != 3 or scores.shape[:2] != keys.shape[:2] or scores.shape[-1] != keys.shape[2]:
            raise RuntimeError(
                "base press returned incompatible scores: "
                f"scores={tuple(scores.shape)} keys={tuple(keys.shape)}"
            )

        cache_length = int(keys.shape[2])
        kept_count = max(1, int(cache_length * (1 - self.compression_ratio)))
        protected = self._valid_indices(
            self.protected_token_indices,
            cache_length,
            scores.device,
        )
        excluded = self._valid_indices(
            self.excluded_token_indices,
            cache_length,
            scores.device,
        )

        if protected.numel() > kept_count and self.strict_protected_budget:
            raise InfeasibleBudgetError(
                "protected authority tokens exceed cache budget: "
                f"protected={protected.numel()} kept={kept_count}"
            )

        adjusted = self._priority_adjusted_scores(
            scores, protected, excluded
        )

        kept_indices = adjusted.topk(kept_count, dim=-1).indices
        gather_indices = kept_indices.unsqueeze(-1).expand(
            -1,
            -1,
            -1,
            keys.shape[-1],
        )

        protected_kept = 0.0
        excluded_kept = 0.0
        if protected.numel() or excluded.numel():
            kept_mask = torch.zeros_like(adjusted, dtype=torch.bool)
            kept_mask.scatter_(-1, kept_indices, True)
            if protected.numel():
                protected_kept = float(
                    kept_mask.index_select(-1, protected).float().mean().item()
                )
            if excluded.numel():
                excluded_kept = float(
                    kept_mask.index_select(-1, excluded).float().mean().item()
                )

        self.audit_records.append(
            {
                "layer": int(getattr(module, "layer_idx", len(self.audit_records))),
                "cache_length": cache_length,
                "kept_count": kept_count,
                "protected_count": int(protected.numel()),
                "excluded_count": int(excluded.numel()),
                "protected_kept_fraction": protected_kept,
                "excluded_kept_fraction": excluded_kept,
                "nonfinite_base_score_count": int(
                    (~torch.isfinite(scores)).sum().item()
                ),
            }
        )

        return (
            keys.gather(2, gather_indices).contiguous(),
            values.gather(2, gather_indices).contiguous(),
        )
