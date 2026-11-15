from __future__ import annotations

import pathlib
import subprocess


ROOT = pathlib.Path(__file__).resolve().parents[1]
QUEUE = ROOT / "scripts" / "run_acl_main_followup_gpu_queue.sh"


def test_followup_queue_has_valid_shell_syntax() -> None:
    subprocess.run(["bash", "-n", str(QUEUE)], check=True, cwd=ROOT)


def test_phi_uses_preoutcome_decode_cap_amendment() -> None:
    text = QUEUE.read_text(encoding="utf-8")
    assert (
        'FOLLOWUP_DECODE_CONFIG='
        '"configs/acl_followup_decode_cap_amendment.json"'
    ) in text
    assert text.count('"$FOLLOWUP_DECODE_CONFIG"') >= 7
    phi_section = text[
        text.index("# Fourth architecture family:")
        : text.index("# Remove the forced JSON assistant prefix")
    ]
    assert " 16 " not in phi_section
    assert phi_section.count(" 32 ") == 5


def test_ih_keeps_task_specific_short_output_cap() -> None:
    text = QUEUE.read_text(encoding="utf-8")
    ih_function = text[text.index("run_ih()"):text.index("ih_fullkv_gate()")]
    assert "--max-new-tokens 16" in ih_function
    assert ih_function.count('--model "$model"') == 1


def test_followup_runners_propagate_failures_before_completion_marker() -> None:
    text = QUEUE.read_text(encoding="utf-8")
    assert "require_success()" in text
    assert "generation_exit_success()" in text
    assert "Missing generation exit metadata" in text
    assert "terminal artifacts are missing" in text
    assert text.count('return "$runner_status"') == 4
    assert 'return "$judge_status"' in text
    for stage in (
        "${tag}_ih_native_fullkv",
        "phi35_fullkv_pilot",
        "qwen_noprefix_fullkv",
        "qwen_systems_nonh2o",
        "agentdojo_fullkv_pilot",
    ):
        assert stage in text
    for status in (
        "systems_summary_status",
        "agentdojo_summary_status",
        "mechanism_summary_status",
    ):
        assert f'if test "${status}" -ne 0; then' in text
    marker_position = text.index(
        'aclfollow_${FOLLOWUP_LABEL}_QUEUE_FINISHED.txt'
    )
    assert marker_position > text.index("mechanism_summary_status")
