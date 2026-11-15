from __future__ import annotations

import pathlib
import subprocess


ROOT = pathlib.Path(__file__).resolve().parents[1]
QUEUE = ROOT / "scripts" / "run_acl_main_gpu_queue.sh"


def test_parent_queue_has_valid_shell_syntax() -> None:
    subprocess.run(["bash", "-n", str(QUEUE)], check=True, cwd=ROOT)


def test_parent_queue_propagates_required_stage_failures() -> None:
    text = QUEUE.read_text(encoding="utf-8")
    assert "require_success()" in text
    assert "Required parent stage failed" in text
    assert 'return "$run_status"' in text
    assert 'return "$judge_status"' in text
    assert "generation_exit_success()" in text
    assert "Missing generation exit metadata" in text
    assert text.count('generation_exit_success "$out_dir" || return $?') == 4
    assert "run_heldout_suite()" in text
    assert "heldout_gate_passes()" in text
    assert "COMPRESSION_SKIPPED_GATE_FAILED.txt" in text
    marker = text.index(
        'aclmain_${RUN_LABEL}_QUEUE_FINISHED.txt'
    )
    assert marker > text.index("run_utility_suite ruler4k")
