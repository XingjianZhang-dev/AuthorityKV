from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_system_ifeval_generation_file_has_no_grader_fields() -> None:
    data_dir = ROOT / "data/external_system_ifeval"
    messages = load_jsonl(data_dir / "sys_ifeval_messages_150.jsonl")
    labels = load_jsonl(data_dir / "sys_ifeval_labels_150.jsonl")
    assert len(messages) == len(labels) == 150
    assert {row["id"] for row in messages} == {row["id"] for row in labels}
    forbidden = {"instruction_id_list", "kwargs", "answers", "expected_behavior"}
    for row in messages:
        assert forbidden.isdisjoint(row)
        assert forbidden.isdisjoint(row["metadata"])
    assert all("instruction_id_list" in row and "kwargs" in row for row in labels)


def test_mixed_evidence_generation_file_has_no_outcome_fields() -> None:
    data_dir = ROOT / "data/mixed_evidence_attack"
    messages = load_jsonl(data_dir / "mixed_evidence_messages_all.jsonl")
    labels = load_jsonl(data_dir / "mixed_evidence_labels.jsonl")
    assert len(messages) == len(labels) == 300
    assert {row["id"] for row in messages} == {row["id"] for row in labels}
    forbidden = {
        "answers",
        "answer",
        "attack_marker",
        "judge_rule",
        "expected_behavior",
    }
    for row in messages:
        assert forbidden.isdisjoint(row)
        assert forbidden.isdisjoint(row["metadata"])
    assert all("answers" in row and "attack_marker" in row for row in labels)


def test_mixed_evidence_pairs_are_complete_and_task_balanced() -> None:
    labels = load_jsonl(
        ROOT / "data/mixed_evidence_attack/mixed_evidence_labels.jsonl"
    )
    by_pair: dict[str, set[str]] = {}
    by_task: dict[str, set[str]] = {}
    for row in labels:
        by_pair.setdefault(row["pair_id"], set()).add(row["condition"])
        by_task.setdefault(row["task"], set()).add(row["pair_id"])
    assert len(by_pair) == 100
    assert all(
        conditions == {"clean", "explicit_attack", "paraphrase_attack"}
        for conditions in by_pair.values()
    )
    assert {task: len(pairs) for task, pairs in by_task.items()} == {
        "2wikimqa": 50,
        "triviaqa": 50,
    }
