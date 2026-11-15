"""Regression tests for IH-Challenge grading and denominator handling."""

from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from run_ih_challenge_kv import official_grade, summarize  # noqa: E402
from run_kvpress_ih_challenge import role_compatible_example  # noqa: E402


GRADER = """
def grade_output_correct(attacker_output, defender_output):
    return attacker_output == "Rome" and defender_output == "city=Rome"
"""


def test_gpu_runners_use_scripts_first_module_resolution() -> None:
    root = SCRIPTS.parent
    for relative_path in (
        "scripts/run_kvpress_ih_challenge.py",
        "scripts/run_kvpress_systems_benchmark.py",
    ):
        text = (root / relative_path).read_text(encoding="utf-8")
        assert 'SCRIPTS = ROOT / "scripts"' in text
        assert "while search_path in sys.path:" in text
        root_insert = "sys.path.insert(0, str(ROOT))"
        scripts_insert = "sys.path.insert(0, str(SCRIPTS))"
        assert root_insert in text
        assert scripts_insert in text
        assert text.index(root_insert) < text.index(scripts_insert)


class DropDeveloperTemplate:
    chat_template = "present"

    def apply_chat_template(
        self,
        messages,
        *,
        tokenize,
        add_generation_prompt,
    ):
        del tokenize, add_generation_prompt
        return "\n".join(
            str(message["content"])
            for message in messages
            if message["role"] in {"system", "user", "assistant"}
        )


class NativeDeveloperTemplate(DropDeveloperTemplate):
    def apply_chat_template(
        self,
        messages,
        *,
        tokenize,
        add_generation_prompt,
    ):
        del tokenize, add_generation_prompt
        return "\n".join(str(message["content"]) for message in messages)


class RejectDeveloperTemplate(DropDeveloperTemplate):
    def apply_chat_template(
        self,
        messages,
        *,
        tokenize,
        add_generation_prompt,
    ):
        if any(message["role"] == "developer" for message in messages):
            raise ValueError("developer role unsupported")
        return super().apply_chat_template(
            messages,
            tokenize=tokenize,
            add_generation_prompt=add_generation_prompt,
        )


def test_native_developer_role_is_left_unchanged() -> None:
    example = {
        "messages": [
            {"role": "developer", "content": "developer rule"},
            {"role": "user", "content": "user task"},
        ]
    }
    adapted, mode = role_compatible_example(NativeDeveloperTemplate(), example)
    assert adapted is example
    assert mode == "native_roles"


def test_dropped_developer_role_is_serialized_and_verified() -> None:
    example = {
        "messages": [
            {"role": "developer", "content": "developer rule"},
            {"role": "user", "content": "user task"},
        ]
    }
    adapted, mode = role_compatible_example(DropDeveloperTemplate(), example)
    assert mode == "control_roles_serialized_in_system_channel"
    assert adapted["messages"][0]["role"] == "system"
    assert "BEGIN ORIGINAL DEVELOPER MESSAGE" in adapted["messages"][0]["content"]
    assert "developer rule" in adapted["messages"][0]["content"]
    assert adapted["messages"][1] == example["messages"][1]


def test_rejected_developer_role_uses_the_same_verified_fallback() -> None:
    example = {
        "messages": [
            {"role": "developer", "content": "developer rule"},
            {"role": "user", "content": "user task"},
        ]
    }
    adapted, mode = role_compatible_example(RejectDeveloperTemplate(), example)
    assert mode.endswith("_after_native_template_error")
    assert "developer rule" in adapted["messages"][0]["content"]
    assert adapted["messages"][1]["content"] == "user task"


def test_dropped_non_control_role_fails_closed() -> None:
    example = {
        "messages": [
            {"role": "tool", "content": "tool result"},
            {"role": "user", "content": "user task"},
        ]
    }
    try:
        role_compatible_example(DropDeveloperTemplate(), example)
    except RuntimeError as exception:
        assert "non-control" in str(exception)
    else:
        raise AssertionError("dropped tool message should fail closed")


def test_official_grader_code_is_used_without_reimplementing_the_task() -> None:
    example = {
        "metadata": {
            "grader_code_python": GRADER,
            "ih_challenge_attack_text": "Rome",
        }
    }
    assert official_grade(example, "city=Rome") == (True, None)
    assert official_grade(example, "city=NONE") == (False, None)


def test_infeasible_rows_are_separate_from_runtime_errors_and_conditioning() -> None:
    base = {
        "method": "authority_streaming_pin",
        "keep_ratio": 0.2,
        "injection_followed": False,
        "grader_error": None,
        "error": None,
    }
    rows = [
        {
            **base,
            "status": "ok",
            "official_correct": True,
            "output_text": "city=Rome",
        },
        {
            **base,
            "status": "infeasible",
            "official_correct": False,
            "output_text": "",
        },
        {
            **base,
            "status": "runtime_error",
            "error": "RuntimeError('boom')",
            "official_correct": False,
            "output_text": "",
        },
    ]
    metrics = summarize(rows)["by_method"]["authority_streaming_pin@0.20"]
    assert metrics["official_accuracy"] == 1 / 3
    assert metrics["conditional_official_accuracy"] == 1.0
    assert metrics["feasibility_rate"] == 2 / 3
    assert metrics["infeasible_num"] == 1
    assert metrics["runtime_error_num"] == 1
