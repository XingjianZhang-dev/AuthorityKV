"""New press variants for the extended experiments (E1 fixed per-layer budget, E2 soft/quota rules, D1 recency tie-break).
Each subclasses the frozen AuthorityAwarePress that is bound in this process (snapshot 870995d2 or current a4af6dc8 via
akv_common.load_runner) and overrides only the selection step. Offsets/budget/audit fields follow the frozen code.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any

import torch
from torch import nn

_wrap = sys.modules["authoritykv_experiments.kvpress_authority"]
AuthorityAwarePress = _wrap.AuthorityAwarePress
InfeasibleBudgetError = _wrap.InfeasibleBudgetError

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from d1_streaming_tiebreak import recency_tiebreak_topk_indices  # noqa: E402


def frozen_adjusted_scores(press, scores: torch.Tensor, protected: torch.Tensor, excluded: torch.Tensor) -> torch.Tensor:
    """The frozen float32 offset rule of whichever wrapper version is loaded (current: _priority_adjusted_scores;
    snapshot: the inline block of compress, reproduced here verbatim in semantics)."""

    if hasattr(press, "_priority_adjusted_scores"):
        return press._priority_adjusted_scores(scores, protected, excluded)
    adjusted = scores.float().clone()
    finite_magnitude = torch.where(torch.isfinite(adjusted), adjusted.abs(), torch.zeros_like(adjusted)).amax(dim=-1, keepdim=True)
    priority_offset = 4.0 * (finite_magnitude + 1.0)
    if excluded.numel():
        adjusted.index_add_(-1, excluded, -priority_offset.expand(*priority_offset.shape[:-1], excluded.numel()))
    if protected.numel():
        adjusted.index_add_(-1, protected, 2.0 * priority_offset.expand(*priority_offset.shape[:-1], protected.numel()))
    return adjusted


def _audit(press, module, scores, adjusted_like, kept_indices, cache_length, kept_count, protected, excluded, extra: dict) -> None:
    protected_kept = 0.0
    excluded_kept = 0.0
    if protected.numel() or excluded.numel():
        kept_mask = torch.zeros(adjusted_like.shape, dtype=torch.bool, device=adjusted_like.device)
        kept_mask.scatter_(-1, kept_indices, True)
        if protected.numel():
            protected_kept = float(kept_mask.index_select(-1, protected).float().mean().item())
        if excluded.numel():
            excluded_kept = float(kept_mask.index_select(-1, excluded).float().mean().item())
    press.audit_records.append({
        "layer": int(getattr(module, "layer_idx", len(press.audit_records))),
        "cache_length": cache_length, "kept_count": kept_count,
        "protected_count": int(protected.numel()), "excluded_count": int(excluded.numel()),
        "protected_kept_fraction": protected_kept, "excluded_kept_fraction": excluded_kept,
        "nonfinite_base_score_count": int((~torch.isfinite(scores)).sum().item()),
        **extra,
    })


def _gather(keys, values, kept_indices):
    g = kept_indices.unsqueeze(-1).expand(-1, -1, -1, keys.shape[-1])
    return keys.gather(2, g).contiguous(), values.gather(2, g).contiguous()


@dataclass
class RecencyTiePress(AuthorityAwarePress):
    """D1: frozen offsets, budget and audit; only the top-k tie handling differs (sink first, then most recent)."""

    n_sink: int = 4

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
            raise InfeasibleBudgetError(f"protected authority tokens exceed cache budget: protected={protected.numel()} kept={kept_count}")
        adjusted = frozen_adjusted_scores(self, scores, protected, excluded)
        kept_indices = recency_tiebreak_topk_indices(adjusted, kept_count, self.n_sink)
        _audit(self, module, scores, adjusted, kept_indices, cache_length, kept_count, protected, excluded, {"tie_break": "recency"})
        return _gather(keys, values, kept_indices)


@dataclass
class FixedCountAuthorityPress(AuthorityAwarePress):
    """E1: same offsets as the frozen wrapper, but kept_count per layer is taken from `layer_kept_counts` (the paired
    full-AKV run's absolute counts). If cache_length <= kept_count the layer is left uncompressed (counted)."""

    layer_kept_counts: dict[int, int] = field(default_factory=dict)
    tie_break: str = "topk"
    n_sink: int = 4

    def compress(self, module: nn.Module, hidden_states, keys, values, attentions, kwargs):
        layer = int(getattr(module, "layer_idx", len(self.audit_records)))
        cache_length = int(keys.shape[2])
        kept_count = int(self.layer_kept_counts[layer])
        scores = self.base_press.score(module, hidden_states, keys, values, attentions, kwargs)
        protected = self._valid_indices(self.protected_token_indices, cache_length, scores.device)
        excluded = self._valid_indices(self.excluded_token_indices, cache_length, scores.device)
        if cache_length <= kept_count:
            self.audit_records.append({"layer": layer, "cache_length": cache_length, "kept_count": cache_length, "target_kept_count": kept_count,
                                       "protected_count": int(protected.numel()), "excluded_count": int(excluded.numel()),
                                       "protected_kept_fraction": 1.0 if protected.numel() else 0.0, "excluded_kept_fraction": 1.0 if excluded.numel() else 0.0,
                                       "uncompressed": True, "tie_break": self.tie_break})
            return keys, values
        if protected.numel() > kept_count and self.strict_protected_budget:
            raise InfeasibleBudgetError(f"protected authority tokens exceed cache budget: protected={protected.numel()} kept={kept_count}")
        adjusted = frozen_adjusted_scores(self, scores, protected, excluded)
        if self.tie_break == "recency":
            kept_indices = recency_tiebreak_topk_indices(adjusted, kept_count, self.n_sink)
        else:
            kept_indices = adjusted.topk(kept_count, dim=-1).indices
        _audit(self, module, scores, adjusted, kept_indices, cache_length, kept_count, protected, excluded, {"uncompressed": False, "target_kept_count": kept_count, "tie_break": self.tie_break})
        return _gather(keys, values, kept_indices)


def soft_adjusted(scores64: torch.Tensor, protected: torch.Tensor, excluded: torch.Tensor, mode: str, strength: float) -> torch.Tensor:
    """E2 soft penalties in float64: s + w * (2*1[P] - 1[D]); w = alpha*sigma_{layer,head} (sigma) or c (const)."""

    sign = torch.zeros_like(scores64)
    if protected.numel():
        sign.index_fill_(-1, protected, 2.0)
    if excluded.numel():
        sign.index_fill_(-1, excluded, -1.0)
    if mode == "sigma":
        w = scores64.std(dim=-1, keepdim=True, unbiased=False) * float(strength)
    elif mode == "const":
        w = torch.full_like(scores64[..., :1], float(strength))
    else:
        raise ValueError(mode)
    return scores64 + w * sign


def quota_select(scores64: torch.Tensor, protected: torch.Tensor, excluded: torch.Tensor, kept_count: int, q: float, demote_d: bool, tie_break: str, n_sink: int) -> torch.Tensor:
    """E2 Quota(q) / Quota+D(q). Selection by base score (float64) inside each pool; ties by topk or recency rule.
    Quota: B_P = min(|P|, floor(q*B)) tokens from P by base score, the remaining B-B_P from all remaining tokens.
    Quota+D: the remaining slots are filled from E and unselected P first, and from D only if slots are left."""

    b, h, n = scores64.shape
    device = scores64.device
    neg = torch.finfo(torch.float64).min
    is_p = torch.zeros(n, dtype=torch.bool, device=device)
    if protected.numel():
        is_p[protected] = True
    is_d = torch.zeros(n, dtype=torch.bool, device=device)
    if excluded.numel():
        is_d[excluded] = True
    b_p = min(int(protected.numel()), int(q * kept_count))
    chosen = torch.zeros((b, h, n), dtype=torch.bool, device=device)

    def pick(mask_allowed: torch.Tensor, k: int) -> None:
        if k <= 0:
            return
        s = torch.where(mask_allowed & ~chosen, scores64, torch.full_like(scores64, neg))
        idx = _recency64(s, k, n_sink) if tie_break == "recency" else s.topk(k, dim=-1).indices
        chosen.scatter_(-1, idx, True)

    pick(is_p.view(1, 1, n).expand(b, h, n), b_p)
    remaining = kept_count - b_p
    if demote_d:
        pool = (~is_d).view(1, 1, n).expand(b, h, n)
        avail = int(min(remaining, (pool[0, 0] & ~chosen[0, 0]).sum().item()))
        pick(pool, avail)
        remaining2 = kept_count - int(chosen[0, 0].sum().item())
        if remaining2 > 0:
            pick(torch.ones((b, h, n), dtype=torch.bool, device=device), remaining2)
    else:
        pick(torch.ones((b, h, n), dtype=torch.bool, device=device), remaining)
    return torch.stack([torch.stack([chosen[i, j].nonzero(as_tuple=True)[0] for j in range(h)]) for i in range(b)])


def _recency64(adjusted: torch.Tensor, kept_count: int, n_sink: int) -> torch.Tensor:
    seq = adjusted.shape[-1]
    positions = torch.arange(seq, device=adjusted.device)
    secondary = torch.where(positions < n_sink, seq + n_sink - positions, positions).to(torch.int64).expand_as(adjusted)
    order_secondary = torch.argsort(secondary, dim=-1, descending=True, stable=True)
    adjusted_by_secondary = torch.gather(adjusted, -1, order_secondary)
    order_primary = torch.argsort(adjusted_by_secondary, dim=-1, descending=True, stable=True)
    final_order = torch.gather(order_secondary, -1, order_primary)
    return final_order[..., :kept_count]


@dataclass
class SoftQuotaPress(AuthorityAwarePress):
    """E2 press. rule ∈ {softsigma, softconst, quota, quotad}; strength = alpha / c / q. Scores in float64."""

    rule: str = "softsigma"
    strength: float = 1.0
    tie_break: str = "topk"
    n_sink: int = 4

    def compress(self, module: nn.Module, hidden_states, keys, values, attentions, kwargs):
        if self.compression_ratio == 0:
            return keys, values
        scores = self.base_press.score(module, hidden_states, keys, values, attentions, kwargs)
        cache_length = int(keys.shape[2])
        kept_count = max(1, int(cache_length * (1 - self.compression_ratio)))
        protected = self._valid_indices(self.protected_token_indices, cache_length, scores.device)
        excluded = self._valid_indices(self.excluded_token_indices, cache_length, scores.device)
        s64 = scores.double()
        if self.rule in ("softsigma", "softconst"):
            adj = soft_adjusted(s64, protected, excluded, "sigma" if self.rule == "softsigma" else "const", self.strength)
            kept_indices = _recency64(adj, kept_count, self.n_sink) if self.tie_break == "recency" else adj.topk(kept_count, dim=-1).indices
        elif self.rule in ("quota", "quotad"):
            kept_indices = quota_select(s64, protected, excluded, kept_count, self.strength, self.rule == "quotad", self.tie_break, self.n_sink)
            adj = s64
        else:
            raise ValueError(self.rule)
        _audit(self, module, scores, adj, kept_indices, cache_length, kept_count, protected, excluded, {"rule": self.rule, "strength": self.strength, "tie_break": self.tie_break})
        return _gather(keys, values, kept_indices)
