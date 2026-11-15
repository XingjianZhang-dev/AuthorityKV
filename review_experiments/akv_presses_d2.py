"""D2 (PREREG-23): seeded random tie-breaking among EXACTLY equal adjusted scores. Everything else (fp32 offsets,
budget, audit) is the frozen rule. The secondary key is a random permutation generated from (seed, example_id, layer)
so it is identical for every arm evaluated on the same example (base with P = D = ∅, full AKV, R+P-strict, E3b)."""

from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass

import torch
from torch import nn

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import akv_presses as PR  # noqa: E402  (frozen_adjusted_scores, _audit, _gather; bound to the loaded wrapper version)

AuthorityAwarePress = PR.AuthorityAwarePress
InfeasibleBudgetError = PR.InfeasibleBudgetError


def random_key(seed: int, example_id: str, layer: int, n: int, device) -> torch.Tensor:
    h = int.from_bytes(hashlib.sha256(f"{seed}\0{example_id}\0{layer}".encode()).digest()[:8], "big") % (2**63 - 1)
    g = torch.Generator(device="cpu").manual_seed(h)
    return torch.randperm(n, generator=g).to(device)


def random_tiebreak_topk_indices(adjusted: torch.Tensor, kept_count: int, secondary: torch.Tensor) -> torch.Tensor:
    """Top-k along the last dim; exact ties broken by the random secondary key (higher key first)."""

    sec = secondary.to(torch.int64).expand_as(adjusted)
    order_secondary = torch.argsort(sec, dim=-1, descending=True, stable=True)
    adjusted_by_secondary = torch.gather(adjusted, -1, order_secondary)
    order_primary = torch.argsort(adjusted_by_secondary, dim=-1, descending=True, stable=True)
    final_order = torch.gather(order_secondary, -1, order_primary)
    return final_order[..., :kept_count]


@dataclass
class RandomTiePress(AuthorityAwarePress):
    tie_seed: int = 1
    example_id: str = ""

    def compress(self, module: nn.Module, hidden_states, keys, values, attentions, kwargs):
        if self.compression_ratio == 0:
            return keys, values
        scores = self.base_press.score(module, hidden_states, keys, values, attentions, kwargs)
        cache_length = int(keys.shape[2])
        kept_count = max(1, int(cache_length * (1 - self.compression_ratio)))
        protected = self._valid_indices(self.protected_token_indices, cache_length, scores.device)
        excluded = self._valid_indices(self.excluded_token_indices, cache_length, scores.device)
        if protected.numel() > kept_count and self.strict_protected_budget:
            raise InfeasibleBudgetError(f"protected authority tokens exceed cache budget: protected={protected.numel()} kept={kept_count}")
        adjusted = PR.frozen_adjusted_scores(self, scores, protected, excluded)
        layer = int(getattr(module, "layer_idx", len(self.audit_records)))
        secondary = random_key(self.tie_seed, self.example_id, layer, cache_length, scores.device)
        kept_indices = random_tiebreak_topk_indices(adjusted, kept_count, secondary)
        PR._audit(self, module, scores, adjusted, kept_indices, cache_length, kept_count, protected, excluded, {"tie_break": f"random{self.tie_seed}"})
        return PR._gather(keys, values, kept_indices)
