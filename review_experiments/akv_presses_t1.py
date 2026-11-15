"""T1 (PREREG-25 amendment B) equivalence twin of akv_presses.RecencyTiePress.

EarliestTiePress is RecencyTiePress with ONE change: the tie key is "earliest position first" instead of
"sinks first, then most recent". Same frozen offsets (frozen_adjusted_scores), same budget formula, same audit,
same gather. If it reproduces the stored paper outputs (torch.topk path) token for token, then the recency code path
differs from the paper implementation only in the direction of exact-tie breaking."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import torch
from torch import nn

sys.path.insert(0, str(Path(__file__).resolve().parent))
import akv_presses as PR  # noqa: E402


def earliest_tiebreak_topk_indices(adjusted: torch.Tensor, kept_count: int) -> torch.Tensor:
    """Top-`kept_count` indices, exact ties broken toward the EARLIEST position. Same two-stable-argsort construction
    as d1_streaming_tiebreak.recency_tiebreak_topk_indices, with secondary key = -position."""

    seq = adjusted.shape[-1]
    positions = torch.arange(seq, device=adjusted.device)
    secondary = (-positions).to(torch.int64).expand_as(adjusted)
    order_secondary = torch.argsort(secondary, dim=-1, descending=True, stable=True)
    adjusted_by_secondary = torch.gather(adjusted, -1, order_secondary)
    order_primary = torch.argsort(adjusted_by_secondary, dim=-1, descending=True, stable=True)
    final_order = torch.gather(order_secondary, -1, order_primary)
    return final_order[..., :kept_count]


@dataclass
class EarliestTiePress(PR.RecencyTiePress):
    """Variant name for configs: tie_break = "earliest" (equivalence twin; not a method)."""

    def compress(self, module: nn.Module, hidden_states, keys, values, attentions, kwargs):
        if self.compression_ratio == 0:
            return keys, values
        base_n_sink = getattr(self.base_press, "n_sink", None)
        if base_n_sink is not None and int(base_n_sink) != int(self.n_sink):
            raise RuntimeError(f"n_sink mismatch: press={self.n_sink} base={base_n_sink}")
        scores = self.base_press.score(module, hidden_states, keys, values, attentions, kwargs)
        cache_length = int(keys.shape[2])
        kept_count = max(1, int(cache_length * (1 - self.compression_ratio)))
        protected = self._valid_indices(self.protected_token_indices, cache_length, scores.device)
        excluded = self._valid_indices(self.excluded_token_indices, cache_length, scores.device)
        if protected.numel() > kept_count and self.strict_protected_budget:
            raise PR.InfeasibleBudgetError(f"protected authority tokens exceed cache budget: protected={protected.numel()} kept={kept_count}")
        adjusted = PR.frozen_adjusted_scores(self, scores, protected, excluded)
        kept_indices = earliest_tiebreak_topk_indices(adjusted, kept_count)
        PR._audit(self, module, scores, adjusted, kept_indices, cache_length, kept_count, protected, excluded, {"tie_break": "earliest"})
        return PR._gather(keys, values, kept_indices)
