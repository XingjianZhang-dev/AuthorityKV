"""Tests for deterministic, suite-wide AgentDojo gate sampling."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_agentdojo_official_kv as runner  # noqa: E402
from run_agentdojo_official_kv import selected_pairs  # noqa: E402
import run_kvpress_authority as kvpress_runner  # noqa: E402


def test_agentdojo_imports_the_registered_scripts_runner() -> None:
    assert Path(kvpress_runner.__file__).resolve() == (
        SCRIPTS / "run_kvpress_authority.py"
    )


def test_bounded_pairs_cover_multiple_users_and_are_deterministic() -> None:
    suite = SimpleNamespace(
        user_tasks={f"u{i}": object() for i in range(10)},
        injection_tasks={f"i{i}": object() for i in range(20)},
    )
    first = selected_pairs(suite, [], [], 10)
    second = selected_pairs(suite, [], [], 10)
    assert first == second
    assert len(first) == len(set(first)) == 10
    assert len({user for user, _ in first}) == 10
    assert len({injection for _, injection in first}) == 10


def test_nonpositive_limit_means_full_explicit_pair_space() -> None:
    suite = SimpleNamespace(user_tasks={}, injection_tasks={})
    pairs = selected_pairs(suite, ["u1", "u0"], ["i1", "i0"], 0)
    assert pairs == [
        ("u0", "i0"),
        ("u0", "i1"),
        ("u1", "i0"),
        ("u1", "i1"),
    ]


def test_registered_agentdojo_gates_cover_both_axes_without_overlap() -> None:
    suite = SimpleNamespace(
        user_tasks={f"user_task_{i}": object() for i in range(40)},
        injection_tasks={
            f"injection_task_{i}": object() for i in range(14)
        },
    )
    pilot = selected_pairs(suite, [], [], 10)
    confirmatory = selected_pairs(suite, [], [], 20)
    assert len({user for user, _ in pilot}) == 10
    assert len({injection for _, injection in pilot}) == 10
    assert len({user for user, _ in confirmatory}) == 20
    assert len({injection for _, injection in confirmatory}) == 14
    assert set(pilot).isdisjoint(confirmatory)


@pytest.mark.parametrize(
    ("method", "expects_attentions"),
    [
        ("kvpress_knorm", False),
        ("kvpress_h2o", True),
    ],
)
def test_agent_step_uses_official_one_shot_kvpress_path(
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    expects_attentions: bool,
) -> None:
    class FakeTokenizer:
        def __call__(self, text, **kwargs):
            assert kwargs["add_special_tokens"] is False
            assert kwargs["return_offsets_mapping"] is True
            return {
                "input_ids": [10, 11, 12],
                "offset_mapping": [(0, 1), (1, 2), (2, 3)],
            }

    captured = {}
    sentinel_press = object()

    def fake_find_spans(prompt, offsets, example, span_source):
        assert prompt == "abc"
        assert offsets == [(0, 1), (1, 2)]
        assert span_source == "metadata"
        return [{"level": "system", "token_indices": [0]}]

    def fake_make_press(got_method, got_keep_ratio, token_spans):
        assert got_method == method
        assert got_keep_ratio == 0.4
        assert token_spans == [{"level": "system", "token_indices": [0]}]
        return sentinel_press

    def fake_generate(**kwargs):
        captured.update(kwargs)
        return {"output_text": "{\"final\":\"ok\"}"}

    monkeypatch.setattr(runner, "find_token_spans", fake_find_spans)
    monkeypatch.setattr(runner, "make_press", fake_make_press)
    monkeypatch.setattr(runner, "generate_kvpress_one", fake_generate)

    pipeline = runner.AuthorityKVAgentDojoPipeline(
        model=object(),
        tokenizer=FakeTokenizer(),
        method=method,
        keep_ratio=0.4,
        max_iters=5,
        max_new_tokens=128,
        quiet=True,
    )
    result = pipeline._generate_json("abc", [], "query")

    assert result["output_text"] == "{\"final\":\"ok\"}"
    assert captured["context_ids"] == [10, 11]
    assert captured["suffix_ids"] == [12]
    assert captured["press"] is sentinel_press
    assert captured["assistant_prefix_ids"] == []
    assert captured["stop_after_json_object"] is True
    assert captured["output_attentions"] is expects_attentions


def test_summary_separates_end_to_end_and_budget_feasible_denominators() -> None:
    records = [
        {
            "method": "kvpress_knorm",
            "keep_ratio": 0.4,
            "pair_id": "p1",
            "status": "ok",
            "utility": True,
            "injection_success": False,
        },
        {
            "method": "kvpress_knorm",
            "keep_ratio": 0.4,
            "pair_id": "p2",
            "status": "infeasible",
            "utility": False,
            "injection_success": False,
        },
    ]
    row = runner.summarize(records, {"p1", "p2"})["by_method"][
        "kvpress_knorm@0.40"
    ]
    assert row["fullkv_filter_den"] == 2
    assert row["budget_feasible_den"] == 1
    assert row["utility_and_safe_rate"] == 0.5
    assert (
        row["conditional_on_budget_feasible"]["utility_and_safe_rate"]
        == 1.0
    )
    assert row["infeasible_num"] == 1
    assert row["runtime_error_num"] == 0
