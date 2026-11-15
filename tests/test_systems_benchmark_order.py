"""Tests for randomized repeated systems-benchmark ordering."""

from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from run_kvpress_systems_benchmark import shuffled_settings  # noqa: E402


def test_order_is_deterministic_and_preserves_every_setting() -> None:
    settings = [
        ("fullkv", 1.0),
        ("kvpress_knorm", 0.2),
        ("kvpress_knorm", 0.4),
        ("authority_knorm_detected_provenance", 0.2),
    ]
    first = shuffled_settings(settings, 7, 1, 2)
    second = shuffled_settings(settings, 7, 1, 2)
    assert first == second
    assert sorted(first) == sorted(settings)


def test_order_changes_across_repeats_or_examples() -> None:
    settings = [(f"m{index}", float(index)) for index in range(9)]
    orders = {
        tuple(shuffled_settings(settings, 7, repeat, example))
        for repeat in range(3)
        for example in range(3)
    }
    assert len(orders) > 1
