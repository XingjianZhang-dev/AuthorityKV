"""D1 draft — recency tie-break for AuthorityAwarePress (sensitivity analysis of an implementation detail).

STATUS: DRAFT written in Stage 2 (read-only stage). NOT executed. In Stage 4 this file is moved verbatim to
`review_experiments/d1_streaming_tiebreak.py` (the only permitted location for new code) and imported from there.
It must not modify the frozen wrapper; it subclasses it and overrides only the top-k selection step.

Motivation (results/RISKS.md R1): StreamingLLMPress scores are binary (1 for the n_sink sinks and the most recent
B - n_sink tokens, 0 elsewhere; external/kvpress/kvpress/presses/streaming_llm_press.py:48-54). After the authority
offsets, every E-tier token inside the recent window has exactly the same adjusted score, so which window tokens are
displaced when P (or added when D frees slots) is decided by `torch.topk` tie-breaking
(authoritykv_experiments/kvpress_authority.py:210) — not by StreamingLLM's semantics.

Variant "recency tie-break": identical offsets (+2Delta for P, -Delta for D, Delta = 4(M+1) in float32),
identical kept_count, identical audit fields. The ONLY change: among equal adjusted scores, prefer
(1) sink positions (< n_sink), then (2) the most recent position (higher absolute index) first.
With P = D = empty this reproduces the official StreamingLLM retained set exactly (the B tokens with score 1 are
selected; no tie inside that set matters). Under pinning, the displaced tokens are the OLDEST window tokens and
slots freed by D are given to the most recent tokens just before the window.

The paper's current tie-break (plain topk) remains the primary configuration; this variant is reported as sensitivity.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn

from authoritykv_experiments.kvpress_authority import AuthorityAwarePress, InfeasibleBudgetError


def recency_tiebreak_topk_indices(
    adjusted: torch.Tensor,
    kept_count: int,
    n_sink: int,
) -> torch.Tensor:
    """Return top-`kept_count` indices along the last dim, breaking exact ties by (sink first, then most recent).

    adjusted: (batch, kv_heads, seq) float32 adjusted scores (offsets already applied).
    Exact-tie semantics: two positions are tied iff their float32 adjusted scores are bitwise equal.
    Implementation: a lexicographic sort (primary = adjusted desc, secondary = recency key desc) built from two
    stable argsorts, which is deterministic on CPU and GPU (no radix-select tie ambiguity).
    """

    seq = adjusted.shape[-1]
    positions = torch.arange(seq, device=adjusted.device)
    # Secondary key: sinks get the largest keys (seq + n_sink - pos), other tokens get their position (recent = larger).
    secondary = torch.where(positions < n_sink, seq + n_sink - positions, positions).to(torch.int64)
    secondary = secondary.expand_as(adjusted)
    order_secondary = torch.argsort(secondary, dim=-1, descending=True, stable=True)
    adjusted_by_secondary = torch.gather(adjusted, -1, order_secondary)
    order_primary = torch.argsort(adjusted_by_secondary, dim=-1, descending=True, stable=True)
    final_order = torch.gather(order_secondary, -1, order_primary)
    return final_order[..., :kept_count]


@dataclass
class AuthorityAwarePressRecencyTie(AuthorityAwarePress):
    """AuthorityAwarePress with StreamingLLM-order tie-breaking. Variant name for configs: `akv_recency_tiebreak`."""

    n_sink: int = 4  # must equal base_press.n_sink (StreamingLLMPress default 4); asserted in compress()

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
        base_n_sink = getattr(self.base_press, "n_sink", None)
        if base_n_sink is not None and int(base_n_sink) != int(self.n_sink):
            raise RuntimeError(f"n_sink mismatch: press={self.n_sink} base={base_n_sink}")

        scores = self.base_press.score(module, hidden_states, keys, values, attentions, kwargs)
        if scores.ndim != 3 or scores.shape[:2] != keys.shape[:2] or scores.shape[-1] != keys.shape[2]:
            raise RuntimeError(f"base press returned incompatible scores: scores={tuple(scores.shape)} keys={tuple(keys.shape)}")

        cache_length = int(keys.shape[2])
        kept_count = max(1, int(cache_length * (1 - self.compression_ratio)))  # identical to the frozen wrapper
        protected = self._valid_indices(self.protected_token_indices, cache_length, scores.device)
        excluded = self._valid_indices(self.excluded_token_indices, cache_length, scores.device)
        if protected.numel() > kept_count and self.strict_protected_budget:
            raise InfeasibleBudgetError(
                f"protected authority tokens exceed cache budget: protected={protected.numel()} kept={kept_count}"
            )
        adjusted = self._priority_adjusted_scores(scores, protected, excluded)  # frozen offset rule, float32

        # === the only behavioural change relative to AuthorityAwarePress.compress ===
        kept_indices = recency_tiebreak_topk_indices(adjusted, kept_count, self.n_sink)
        # ============================================================================

        gather_indices = kept_indices.unsqueeze(-1).expand(-1, -1, -1, keys.shape[-1])
        protected_kept = 0.0
        excluded_kept = 0.0
        if protected.numel() or excluded.numel():
            kept_mask = torch.zeros_like(adjusted, dtype=torch.bool)
            kept_mask.scatter_(-1, kept_indices, True)
            if protected.numel():
                protected_kept = float(kept_mask.index_select(-1, protected).float().mean().item())
            if excluded.numel():
                excluded_kept = float(kept_mask.index_select(-1, excluded).float().mean().item())
        self.audit_records.append(
            {
                "layer": int(getattr(module, "layer_idx", len(self.audit_records))),
                "cache_length": cache_length,
                "kept_count": kept_count,
                "protected_count": int(protected.numel()),
                "excluded_count": int(excluded.numel()),
                "protected_kept_fraction": protected_kept,
                "excluded_kept_fraction": excluded_kept,
                "nonfinite_base_score_count": int((~torch.isfinite(scores)).sum().item()),
                "tie_break": "recency",
            }
        )
        return keys.gather(2, gather_indices).contiguous(), values.gather(2, gather_indices).contiguous()


# Planned unit checks (Stage 4, pytest under review_experiments/tests/):
# 1. P = D = empty, StreamingLLM scores -> retained set == official StreamingLLMPress retained set (exact indices).
# 2. Synthetic 0/1 scores with 31 P tokens outside the window -> the 31 displaced tokens are the 31 oldest window tokens
#    (lowest positions >= window start), never the last tokens.
# 3. Continuous scores without exact ties -> identical to torch.topk selection (set equality).
