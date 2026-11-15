"""Tests for IH-Challenge aggregate and paired statistics."""

from __future__ import annotations

import random
import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from summarize_ih_challenge_runs import (  # noqa: E402
    paired_comparison,
    summarize_group,
)


def row(example_id: str, correct: bool, status: str = "ok") -> dict:
    return {
        "example_id": example_id,
        "example_index": int(example_id[-1]),
        "model": "model",
        "dataset": "data.jsonl",
        "method": "kvpress_streaming",
        "keep_ratio": 0.2,
        "status": status,
        "error": None,
        "grader_error": None,
        "official_correct": correct,
        "injection_followed": not correct,
        "prompt_tokens": 100,
        "retained_prompt_tokens": 20,
        "prefill_seconds": 0.1,
        "elapsed_seconds": 0.2,
        "peak_memory_mb": 1000,
        "press_audit": [],
    }


def test_group_reports_end_to_end_and_conditional_denominators() -> None:
    rows = [row("x0", True), row("x1", False, status="infeasible")]
    summary = summarize_group(rows)
    assert summary["end_to_end_accuracy"] == 0.5
    assert summary["conditional_accuracy"] == 1.0
    assert summary["infeasible_num"] == 1
    assert summary["actual_keep_ratio_median"] == 0.2


def test_paired_comparison_uses_only_jointly_eligible_examples() -> None:
    base = [row("x0", False), row("x1", True), row("x2", True)]
    comparison = [row("x0", True), row("x1", True), row("x2", False, "infeasible")]
    result = paired_comparison(base, comparison, 100, random.Random(7))
    assert result is not None
    assert result["paired_num"] == 2
    assert result["base_correct_num"] == 1
    assert result["comparison_correct_num"] == 2
    assert result["comparison_only_correct_n01"] == 1


def test_primary_pairing_filters_to_fullkv_correct_examples() -> None:
    base = [row("x0", False), row("x1", True), row("x2", False)]
    comparison = [row("x0", True), row("x1", True), row("x2", True)]
    result = paired_comparison(
        base,
        comparison,
        100,
        random.Random(7),
        eligible_example_ids={"x0", "x1"},
    )
    assert result is not None
    assert result["paired_scope"] == "fullkv_correct_and_jointly_eligible"
    assert result["fullkv_correct_pool_num"] == 2
    assert result["paired_num"] == 2
    assert result["base_correct_num"] == 1
    assert result["comparison_correct_num"] == 2


def test_group_retains_end_to_end_and_fullkv_filtered_metrics() -> None:
    rows = [row("x0", True), row("x1", False), row("x2", True)]
    summary = summarize_group(rows, {"x0", "x1"})
    assert summary["end_to_end_accuracy_den"] == 3
    assert summary["fullkv_correct_pool_num"] == 2
    assert summary["fullkv_filtered_accuracy_num"] == 1
    assert summary["fullkv_filtered_accuracy_den"] == 2
