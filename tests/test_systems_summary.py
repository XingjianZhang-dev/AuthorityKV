"""Tests for paired systems bootstrap and eligibility."""

from __future__ import annotations

import random
import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from summarize_systems_benchmark import (  # noqa: E402
    eligible,
    paired_bootstrap_median_delta,
    per_example_median_deltas,
)


def test_paired_bootstrap_constant_delta_is_exact() -> None:
    low, high = paired_bootstrap_median_delta(
        [2.0, 2.0, 2.0],
        100,
        random.Random(7),
    )
    assert low == high == 2.0


def test_only_successful_error_free_rows_are_eligible() -> None:
    assert eligible({"status": "ok", "error": None})
    assert not eligible({"status": "runtime_error", "error": "boom"})
    assert not eligible({"status": "infeasible", "error": None})


def test_repeated_measurements_are_aggregated_to_prompt_units() -> None:
    pairs = []
    for example_id, deltas in {
        "example_a": [0.0, 0.0, 100.0],
        "example_b": [10.0, 10.0, 10.0],
    }.items():
        for repeat, delta in enumerate(deltas):
            baseline = {
                "example_id": example_id,
                "repeat": repeat,
                "elapsed_seconds": 1.0,
            }
            comparison = {
                "example_id": example_id,
                "repeat": repeat,
                "elapsed_seconds": 1.0 + delta,
            }
            pairs.append((baseline, comparison))
    assert per_example_median_deltas(
        pairs,
        "elapsed_seconds",
    ) == [0.0, 10.0]
