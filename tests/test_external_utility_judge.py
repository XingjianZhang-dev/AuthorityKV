"""Regression tests for public utility-task scoring."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from run_external_utility_kv import judge_output, official_longbench_score
from summarize_external_utility_runs import paired_utility_comparisons


def test_empty_output_never_matches_nonempty_answer() -> None:
    result = judge_output("", ["5762943"], "ruler_string_match_all")
    assert result["correct"] is False
    assert result["answer_match_fraction"] == 0.0


def test_ruler_requires_every_reference_answer() -> None:
    partial = judge_output("alpha", ["alpha", "beta"], "ruler_string_match_all")
    complete = judge_output("alpha and beta", ["alpha", "beta"], "ruler_string_match_all")
    assert partial["correct"] is False
    assert complete["correct"] is True


def test_ruler_rejects_a_numeric_answer_prefix() -> None:
    partial = judge_output("5762", ["5762943"], "ruler_string_match_all")
    complete = judge_output(
        "The special magic number is 5762943.",
        ["5762943"],
        "ruler_string_match_all",
    )
    assert partial["correct"] is False
    assert complete["correct"] is True


def test_longbench_qa_f1_is_zero_for_empty_prediction() -> None:
    assert official_longbench_score("triviaqa", "", ["James Woods"]) == 0.0


def test_paired_utility_summary_matches_fullkv_by_example() -> None:
    dataset = "data/external_utility/longbench_official_triviaqa_50.jsonl"
    records = []
    for example_id, score in (("a", 0.8), ("b", 0.6)):
        records.extend(
            [
                {
                    "dataset": dataset,
                    "method": "fullkv",
                    "keep_ratio": 1.0,
                    "example_id": example_id,
                    "longbench_score": score,
                    "correct": True,
                    "error": None,
                },
                {
                    "dataset": dataset,
                    "method": (
                        "authority_streaming_detected_provenance"
                    ),
                    "keep_ratio": 0.2,
                    "example_id": example_id,
                    "longbench_score": score,
                    "correct": True,
                    "error": None,
                },
            ]
        )
    rows = paired_utility_comparisons(
        records,
        bootstrap_samples=100,
        seed=7,
    )
    assert len(rows) == 1
    row = rows[0]
    assert row["paired_num"] == 2
    assert row["missing_or_unscored_pair_num"] == 0
    assert row["score_field"] == "longbench_score"
    assert row["fullkv_score"] == 0.7
    assert row["comparison_score"] == 0.7
    assert row["absolute_score_delta_ci95_low"] == 0.0
    assert row["absolute_score_delta_ci95_high"] == 0.0


def test_paired_utility_summary_uses_accuracy_for_ruler() -> None:
    dataset = "data/external_utility/ruler_official_qwen25_4k_24.jsonl"
    records = [
        {
            "dataset": dataset,
            "method": method,
            "keep_ratio": ratio,
            "example_id": "ruler-a",
            "longbench_score": 0.0,
            "correct": correct,
            "error": None,
        }
        for method, ratio, correct in (
            ("fullkv", 1.0, True),
            ("authority_h2o_detected_provenance", 0.4, False),
        )
    ]
    rows = paired_utility_comparisons(
        records,
        bootstrap_samples=20,
        seed=9,
    )
    assert len(rows) == 1
    assert rows[0]["score_field"] == "utility_accuracy"
    assert rows[0]["fullkv_score"] == 1.0
    assert rows[0]["comparison_score"] == 0.0
    assert rows[0]["absolute_score_delta_ci95_low"] == -1.0
