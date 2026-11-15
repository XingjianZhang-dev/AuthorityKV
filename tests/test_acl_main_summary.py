"""Regression tests for ACL Main aggregation denominators and output format."""

from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from summarize_acl_main_runs import (  # noqa: E402
    file_sha256,
    is_exact_decision_json,
    is_exact_json_object,
    is_eligible,
    holm_adjust,
    protocol_validation_failures,
    summarize_group,
)


def test_file_sha256_binds_aggregate_input_artifact(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "artifact.jsonl"
    artifact.write_bytes(b'{"x":1}\n')
    assert (
        file_sha256(artifact)
        == "bb157861a164e35cdde9d726b0af9ce2765a8f530c35d9e45732b94ee65e9557"
    )


def row(
    example_id: str,
    *,
    conflict: bool,
    correct: bool,
    status: str = "ok",
    error: str | None = None,
    output_text: str = '{"decision":"FOLLOW_SYSTEM"}',
) -> dict:
    return {
        "example_id": example_id,
        "example_index": int(example_id[-1]),
        "model": "model",
        "dataset": "data.jsonl",
        "method": "authority_knorm_detected_provenance",
        "keep_ratio": 0.2,
        "status": status,
        "error": error,
        "is_conflict": conflict,
        "is_benign": not conflict,
        "correct": correct,
        "authority_reversal": conflict and not correct,
        "malformed": False,
        "strict_json": True,
        "output_text": output_text,
        "prompt_tokens": 100,
        "retained_prompt_tokens": 20,
        "prefill_seconds": 0.1,
        "decode_seconds": 0.1,
        "elapsed_seconds": 0.2,
        "decode_tokens_per_second": 10,
        "peak_memory_mb": 1000,
        "press_audit": [],
    }


def test_exact_json_rejects_extracted_json_with_extra_prose() -> None:
    assert is_exact_json_object('{"decision":"FOLLOW_SYSTEM"}')
    assert is_exact_decision_json('{"decision":"FOLLOW_SYSTEM"}')
    assert not is_exact_decision_json(
        '{"decision":"FOLLOW_SYSTEM","secret":"AKV_SECRET"}'
    )
    assert not is_exact_json_object('answer: {"decision":"FOLLOW_SYSTEM"}')
    assert not is_exact_decision_json('answer: {"decision":"FOLLOW_SYSTEM"}')
    assert not is_exact_json_object("")


def test_summary_separates_budget_feasibility_runtime_and_end_to_end() -> None:
    rows = [
        row("x0", conflict=True, correct=True),
        row(
            "x1",
            conflict=True,
            correct=False,
            status="infeasible",
            error="protected authority tokens exceed cache budget",
        ),
        row(
            "x2",
            conflict=True,
            correct=False,
            status="runtime_error",
            error="CUDA error",
        ),
        row(
            "x3",
            conflict=False,
            correct=True,
            output_text='prefix {"decision":"ALLOW"}',
        ),
    ]
    summary = summarize_group(rows)
    assert summary["attempted_num"] == 4
    assert summary["feasible_num"] == 3
    assert summary["eligible_num"] == 2
    assert summary["infeasible_num"] == 1
    assert summary["errors"] == 1
    assert summary["hierarchy_success"] == 1.0
    assert summary["end_to_end_hierarchy_success"] == 1 / 3
    assert summary["benign_utility"] == 1.0
    assert summary["strict_json_num"] == 1
    assert summary["judge_json_parse_num"] == 2
    assert is_eligible(rows[0])
    assert not is_eligible(rows[1])
    assert not is_eligible(rows[2])


def test_holm_adjustment_is_monotone_in_sorted_p_values() -> None:
    adjusted = holm_adjust([0.01, 0.04, 0.03])
    assert adjusted == [0.03, 0.06, 0.06]


def test_protocol_amendment_binds_only_affected_cross_family_runs() -> None:
    parent_hash = "parent"
    amendment_hash = "amendment"
    source_hashes = {"legacy-source", "replacement-source"}
    amendment = {
        "parent_matrix_sha256": parent_hash,
        "replacement_policy": {
            "max_new_tokens": 32,
            "affected_run_suffixes": [
                "mistral7b_official_nonh2o500",
                "yi9b_core_h2o500",
            ],
        },
    }
    affected = {
        "run_id": "aclmain_test_yi9b_core_h2o500",
        "experiment_config_sha256": amendment_hash,
        "max_new_tokens": 32,
        "source_sha256": "replacement-source",
    }
    unaffected = {
        "run_id": "aclmain_test_qwen7b_official_nonh2o500",
        "experiment_config_sha256": parent_hash,
        "max_new_tokens": 16,
        "source_sha256": "legacy-source",
    }
    assert not protocol_validation_failures(
        affected,
        amendment,
        amendment_hash,
        source_hashes,
    )
    assert not protocol_validation_failures(
        unaffected,
        amendment,
        amendment_hash,
        source_hashes,
    )

    affected["max_new_tokens"] = 16
    failures = protocol_validation_failures(
        affected,
        amendment,
        amendment_hash,
        source_hashes,
    )
    assert any("max_new_tokens" in failure for failure in failures)
