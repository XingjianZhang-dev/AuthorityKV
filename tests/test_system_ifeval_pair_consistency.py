import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
METRICS = (
    ROOT
    / "reports/arr_august_external_closure/full/system_ifeval_full_v4_metrics.json"
)


def test_system_ifeval_scoring_is_seeded_and_pair_consistent() -> None:
    data = json.loads(METRICS.read_text())
    controls = data["grader_determinism"]
    assert controls == {
        "langdetect_detector_factory_seed": 0,
        "paired_aggregate_consistency": True,
        "python_random_seed": 0,
    }

    expected = {
        "kvpress_streaming@0.40": (11, 8),
        "authority_streaming_detected_provenance@0.40": (61, 48),
        "kvpress_knorm@0.40": (28, 24),
        "authority_knorm_detected_provenance@0.40": (71, 56),
    }
    for method, (all_count, gated_count) in expected.items():
        assert data["by_method"][method]["all_prompts"]["prompt_strict_num"] == all_count
        assert (
            data["by_method"][method]["fullkv_strict_correct_prompts"][
                "prompt_strict_num"
            ]
            == gated_count
        )

    for comparison_name, scopes in data["paired_comparisons"].items():
        base, authority = comparison_name.split("_vs_", 1)
        for scope, comparison in scopes.items():
            table = comparison["prompt_strict"]
            aggregate_scope = (
                "all_prompts"
                if scope == "all_prompts"
                else "fullkv_strict_correct_prompts"
            )
            assert table["base_only"] + table["both"] == data["by_method"][base][
                aggregate_scope
            ]["prompt_strict_num"]
            assert table["authority_only"] + table["both"] == data["by_method"][
                authority
            ][aggregate_scope]["prompt_strict_num"]
            assert (
                table["base_only"]
                + table["authority_only"]
                + table["both"]
                + table["neither"]
                == comparison["pairs"]
            )
