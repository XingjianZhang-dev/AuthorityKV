"""Layer-budget-faithful AuthorityKV wrapper for isolated follow-up studies.

This module is intentionally separate from the frozen preregistered runner.
It preserves a scorer press's layer-specific cache allocation (notably
PyramidKV) while changing only the priority assigned to authority spans.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn

from .kvpress_authority import AuthorityAwarePress, InfeasibleBudgetError


@dataclass
class LayerBudgetAwareAuthorityPress(AuthorityAwarePress):
    """Apply authority priorities without changing the base layer budget."""

    def _kept_count(self, module: nn.Module, cache_length: int) -> int:
        layer_budget = getattr(self.base_press, "get_layer_budget", None)
        if callable(layer_budget):
            kept_count = int(layer_budget(module, cache_length))
        else:
            kept_count = int(
                cache_length * (1 - self.compression_ratio)
            )
        if not 1 <= kept_count <= cache_length:
            raise RuntimeError(
                "base press returned an invalid layer budget: "
                f"kept={kept_count} cache_length={cache_length}"
            )
        return kept_count

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
        if (
            scores.ndim != 3
            or scores.shape[:2] != keys.shape[:2]
            or scores.shape[-1] != keys.shape[2]
        ):
            raise RuntimeError(
                "base press returned incompatible scores: "
                f"scores={tuple(scores.shape)} keys={tuple(keys.shape)}"
            )

        cache_length = int(keys.shape[2])
        kept_count = self._kept_count(module, cache_length)
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

        if (
            protected.numel() > kept_count
            and self.strict_protected_budget
        ):
            raise InfeasibleBudgetError(
                "protected authority tokens exceed layer cache budget: "
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
                    kept_mask.index_select(-1, protected)
                    .float()
                    .mean()
                    .item()
                )
            if excluded.numel():
                excluded_kept = float(
                    kept_mask.index_select(-1, excluded)
                    .float()
                    .mean()
                    .item()
                )

        self.audit_records.append(
            {
                "layer": int(
                    getattr(module, "layer_idx", len(self.audit_records))
                ),
                "cache_length": cache_length,
                "kept_count": kept_count,
                "protected_count": int(protected.numel()),
                "excluded_count": int(excluded.numel()),
                "protected_kept_fraction": protected_kept,
                "excluded_kept_fraction": excluded_kept,
                "nonfinite_base_score_count": int(
                    (~torch.isfinite(scores)).sum().item()
                ),
                "layer_budget_source": (
                    "base_press"
                    if callable(
                        getattr(
                            self.base_press,
                            "get_layer_budget",
                            None,
                        )
                    )
                    else "compression_ratio"
                ),
            }
        )

        return (
            keys.gather(2, gather_indices).contiguous(),
            values.gather(2, gather_indices).contiguous(),
        )
