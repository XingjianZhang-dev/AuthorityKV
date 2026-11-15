"""Unit tests for the common-harness AuthorityKV press."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
import torch

from authoritykv_experiments.kvpress_authority import (
    AuthorityAwarePress,
    InfeasibleBudgetError,
)
from kvpress.presses.scorer_press import ScorerPress


class PositionScorePress(ScorerPress):
    """Assign increasing importance to later token positions."""

    def score(self, module, hidden_states, keys, values, attentions, kwargs):
        positions = keys[..., 0]
        return positions


class NonfiniteScorePress(ScorerPress):
    """Exercise scorers that use infinities as selection sentinels."""

    def score(self, module, hidden_states, keys, values, attentions, kwargs):
        scores = torch.full(
            keys.shape[:3],
            float("-inf"),
            dtype=keys.dtype,
            device=keys.device,
        )
        scores[..., -2] = float("inf")
        scores[..., -1] = float("nan")
        return scores


def make_cache(length: int = 10) -> tuple[torch.Tensor, torch.Tensor]:
    positions = torch.arange(length, dtype=torch.float32).view(1, 1, length, 1)
    keys = positions.expand(1, 2, length, 4).contiguous()
    values = (positions + 100).expand(1, 2, length, 4).contiguous()
    return keys, values


def selected_positions(keys: torch.Tensor) -> set[int]:
    return {int(value) for value in keys[0, 0, :, 0].tolist()}


def test_protected_tokens_override_base_ranking() -> None:
    keys, values = make_cache()
    press = AuthorityAwarePress(
        base_press=PositionScorePress(compression_ratio=0.5),
        compression_ratio=0.5,
        protected_token_indices=(0, 1),
    )
    compressed_keys, _ = press.compress(
        SimpleNamespace(layer_idx=0),
        torch.empty(1, 10, 4),
        keys,
        values,
        None,
        {},
    )
    assert selected_positions(compressed_keys) == {0, 1, 7, 8, 9}
    assert press.audit_records[0]["protected_kept_fraction"] == 1.0


def test_excluded_tokens_lose_to_eligible_tokens() -> None:
    keys, values = make_cache()
    press = AuthorityAwarePress(
        base_press=PositionScorePress(compression_ratio=0.5),
        compression_ratio=0.5,
        excluded_token_indices=(8, 9),
    )
    compressed_keys, _ = press.compress(
        SimpleNamespace(layer_idx=0),
        torch.empty(1, 10, 4),
        keys,
        values,
        None,
        {},
    )
    assert selected_positions(compressed_keys) == {3, 4, 5, 6, 7}
    assert press.audit_records[0]["excluded_kept_fraction"] == 0.0


def test_protection_wins_over_exclusion() -> None:
    keys, values = make_cache()
    press = AuthorityAwarePress(
        base_press=PositionScorePress(compression_ratio=0.5),
        compression_ratio=0.5,
        protected_token_indices=(0,),
        excluded_token_indices=(0, 9),
    )
    compressed_keys, _ = press.compress(
        SimpleNamespace(layer_idx=0),
        torch.empty(1, 10, 4),
        keys,
        values,
        None,
        {},
    )
    assert 0 in selected_positions(compressed_keys)
    assert 9 not in selected_positions(compressed_keys)


def test_impossible_protected_budget_fails_closed() -> None:
    keys, values = make_cache()
    press = AuthorityAwarePress(
        base_press=PositionScorePress(compression_ratio=0.8),
        compression_ratio=0.8,
        protected_token_indices=(0, 1, 2),
    )
    with pytest.raises(InfeasibleBudgetError, match="protected authority tokens exceed"):
        press.compress(
            SimpleNamespace(layer_idx=0),
            torch.empty(1, 10, 4),
            keys,
            values,
            None,
            {},
        )


def test_adaptive_budget_keeps_best_protected_subset() -> None:
    keys, values = make_cache()
    press = AuthorityAwarePress(
        base_press=PositionScorePress(compression_ratio=0.8),
        compression_ratio=0.8,
        protected_token_indices=(0, 1, 2),
        strict_protected_budget=False,
    )
    compressed_keys, _ = press.compress(
        SimpleNamespace(layer_idx=0),
        torch.empty(1, 10, 4),
        keys,
        values,
        None,
        {},
    )
    assert selected_positions(compressed_keys) == {2}
    assert press.audit_records[0]["protected_kept_fraction"] == pytest.approx(
        1 / 3
    )


def test_nonfinite_base_scores_preserve_authority_tier_order() -> None:
    keys, values = make_cache()
    press = AuthorityAwarePress(
        base_press=NonfiniteScorePress(compression_ratio=0.5),
        compression_ratio=0.5,
        protected_token_indices=(0,),
        excluded_token_indices=(8, 9),
    )
    compressed_keys, _ = press.compress(
        SimpleNamespace(layer_idx=0),
        torch.empty(1, 10, 4),
        keys,
        values,
        None,
        {},
    )
    selected = selected_positions(compressed_keys)
    assert 0 in selected
    assert 8 not in selected
    assert 9 not in selected
    assert press.audit_records[0]["protected_kept_fraction"] == 1.0
    assert press.audit_records[0]["excluded_kept_fraction"] == 0.0
    assert press.audit_records[0]["nonfinite_base_score_count"] == 20


def test_protected_and_excluded_overlap_is_canonicalized_to_protected() -> None:
    press = AuthorityAwarePress(
        base_press=PositionScorePress(compression_ratio=0.5),
        compression_ratio=0.5,
        protected_token_indices=(0, 1),
        excluded_token_indices=(1, 2),
    )
    assert press.protected_token_indices == (0, 1)
    assert press.excluded_token_indices == (2,)
