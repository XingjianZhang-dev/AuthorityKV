"""Tests for official-press composition in the common GPU harness."""

from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from run_kvpress_authority import COMPOSED_METHODS, make_press  # noqa: E402


TOKEN_SPANS = [
    {"level": "system", "token_indices": [1, 2], "text": "system control"},
    {"level": "developer", "token_indices": [3, 4], "text": "developer control"},
    {"level": "user", "token_indices": [5, 6], "text": "ordinary user request"},
    {
        "level": "retrieved_document",
        "token_indices": [7, 8],
        "text": "untrusted retrieved observation",
    },
]


def test_composed_method_registry_contains_each_required_control() -> None:
    required = {
        "system_streaming_pin",
        "all_control_streaming_pin",
        "authority_streaming_pin",
        "authority_streaming_detected_provenance",
        "system_knorm_pin",
        "all_control_knorm_pin",
        "authority_knorm_pin",
        "authority_knorm_detected_provenance",
        "system_h2o_pin",
        "all_control_h2o_pin",
        "authority_h2o_pin",
        "authority_h2o_detected_provenance",
    }
    assert required <= COMPOSED_METHODS


def test_streaming_composition_uses_upstream_streaming_press() -> None:
    press = make_press("authority_streaming_detected_provenance", 0.2, TOKEN_SPANS)
    assert type(press.base_press).__name__ == "StreamingLLMPress"
    assert press.protected_token_indices == (1, 2, 3, 4)
    assert set(press.excluded_token_indices) == {7, 8}


def test_knorm_composition_uses_upstream_knorm_press() -> None:
    press = make_press("authority_knorm_detected_provenance", 0.4, TOKEN_SPANS)
    assert type(press.base_press).__name__ == "KnormPress"
    assert press.protected_token_indices == (1, 2, 3, 4)
    assert set(press.excluded_token_indices) == {7, 8}


def test_h2o_composition_uses_upstream_observed_attention_press() -> None:
    press = make_press("authority_h2o_detected_provenance", 0.4, TOKEN_SPANS)
    assert type(press.base_press).__name__ == "ObservedAttentionPress"
    assert press.protected_token_indices == (1, 2, 3, 4)
    assert set(press.excluded_token_indices) == {7, 8}


def test_simple_controls_have_distinct_protection_sets() -> None:
    system = make_press("system_streaming_pin", 0.2, TOKEN_SPANS)
    all_control = make_press("all_control_streaming_pin", 0.2, TOKEN_SPANS)
    assert system.protected_token_indices == (1, 2)
    assert all_control.protected_token_indices == (1, 2, 3, 4, 5, 6, 7, 8)
