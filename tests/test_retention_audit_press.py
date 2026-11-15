"""Tests for outcome-informed KV retention instrumentation."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import torch

from kvpress.presses.scorer_press import ScorerPress

from authoritykv_experiments.retention_audit_press import (
    RetentionAuditPress,
)


@dataclass
class PositionScorer(ScorerPress):
    def score(
        self,
        module,
        hidden_states,
        keys,
        values,
        attentions,
        kwargs,
    ):
        positions = torch.arange(
            keys.shape[2],
            dtype=keys.dtype,
            device=keys.device,
        )
        return positions.view(1, 1, -1).expand(
            keys.shape[0],
            keys.shape[1],
            -1,
        )


@dataclass
class LayerBudgetPositionScorer(PositionScorer):
    def get_layer_budget(self, module, q_len):
        return 3


def tensors():
    keys = torch.arange(1 * 2 * 10 * 3, dtype=torch.float32).reshape(
        1, 2, 10, 3
    )
    values = keys + 1000
    hidden = torch.zeros(1, 10, 6)
    module = SimpleNamespace(layer_idx=2, head_dim=3)
    return module, hidden, keys, values


def test_audit_wrapper_is_numerically_identical_to_official_topk() -> None:
    module, hidden, keys, values = tensors()
    official = PositionScorer(compression_ratio=0.6)
    expected_keys, expected_values = official.compress(
        module, hidden, keys, values, None, {}
    )
    audited = RetentionAuditPress(
        base_press=PositionScorer(compression_ratio=0.6),
        compression_ratio=0.6,
        token_groups={"early": [0, 1], "late": [8, 9]},
    )
    actual_keys, actual_values = audited.compress(
        module, hidden, keys, values, None, {}
    )
    assert torch.equal(actual_keys, expected_keys)
    assert torch.equal(actual_values, expected_values)
    record = audited.audit_records[0]
    assert record["kept_count"] == 4
    assert record["early_kept_fraction"] == 0.0
    assert record["late_kept_fraction"] == 1.0
    assert len(record["selection_indices_sha256"]) == 64


def test_audit_wrapper_preserves_layer_specific_budget() -> None:
    module, hidden, keys, values = tensors()
    audited = RetentionAuditPress(
        base_press=LayerBudgetPositionScorer(compression_ratio=0.6),
        compression_ratio=0.6,
    )
    actual_keys, _ = audited.compress(
        module, hidden, keys, values, None, {}
    )
    assert actual_keys.shape[2] == 3
    assert audited.audit_records[0]["kept_count"] == 3
