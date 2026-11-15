import json
import sys
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from summarize_matched_causal_followup import evaluate  # noqa: E402


def make_rows() -> tuple[dict, list[dict], list[dict]]:
    config = json.loads(
        (
            ROOT
            / "configs"
            / "acl_main_matched_causal_followup.json"
        ).read_text(encoding="utf-8")
    )
    methods = config["run"]["methods"]
    rows: list[dict] = []
    prior: list[dict] = []
    for index in range(30):
        is_conflict = index < 25
        example_id = (
            f"conflict_{index:02d}"
            if is_conflict
            else f"benign_{index:02d}"
        )
        for method in methods:
            if "matched_wrong_authority" in method:
                correct = (index < 2) if is_conflict else True
            elif method.endswith("_v2_adaptive"):
                correct = (index < 20) if is_conflict else True
            else:
                correct = (index < 15) if is_conflict else True
            base = method.split("_")[1]
            output_text = (
                '{"decision":"ALLOW"}'
                if not is_conflict
                else (
                    '{"decision":"FOLLOW_SYSTEM"}'
                    if correct
                    else '{"decision":"FOLLOW_USER"}'
                )
            )
            row = {
                "example_id": example_id,
                "method": method,
                "keep_ratio": 0.02,
                "status": "ok",
                "error": None,
                "infeasible_reason": None,
                "is_conflict": is_conflict,
                "is_benign": not is_conflict,
                "correct": correct,
                "output_text": output_text,
                "generated_token_ids": (
                    [1, 2, 3]
                    if not is_conflict
                    else ([4] if correct else [5])
                ),
                "generation_tokens": 3 if not is_conflict else 1,
                "max_new_tokens": 16,
                "retained_prompt_tokens": 162.0,
                "retained_prompt_tokens_min": 162,
                "retained_prompt_tokens_max": 162,
                "layerwise_mask_adapter_activated": base == "pyramid",
            }
            rows.append(row)
            if (
                method.startswith("kvpress_")
                or method.endswith("_v2_adaptive")
            ):
                prior.append(deepcopy(row))
    return config, rows, prior


def test_matched_causal_summary_passes_registered_design() -> None:
    config, rows, prior = make_rows()
    report = evaluate(config, rows, rows, prior)
    assert report["status"] == "PASS"
    assert report["causal_authority_selection_supported"] is True
    assert report["official_and_correct_reproduction_rows"] == 180
    assert all(
        row["benign_exact_output_matches"] == 5
        for row in report["comparisons"]
    )


def test_matched_causal_summary_fails_benign_treatment_mismatch() -> None:
    config, rows, prior = make_rows()
    for row in rows:
        if (
            row["example_id"] == "benign_25"
            and "matched_wrong_authority" in row["method"]
        ):
            row["output_text"] = '{"decision":"REFUSE"}'
            row["generated_token_ids"] = [9]
    report = evaluate(config, rows, rows, prior)
    assert report["status"] == "FAIL"
    assert report["causal_authority_selection_supported"] is False
