import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from judge_authoritykv import generation_cap_counts  # noqa: E402


def test_generation_cap_counts_excludes_missing_metadata() -> None:
    records = [
        {"generation_tokens": None, "max_new_tokens": None},
        {"generation_tokens": None, "max_new_tokens": 16},
        {},
    ]
    assert generation_cap_counts(records) == (0, 0)


def test_generation_cap_counts_uses_only_integer_pairs() -> None:
    records = [
        {"generation_tokens": 16, "max_new_tokens": 16},
        {"generation_tokens": 7, "max_new_tokens": 16},
        {"generation_tokens": True, "max_new_tokens": 1},
        {"generation_tokens": "16", "max_new_tokens": 16},
    ]
    assert generation_cap_counts(records) == (1, 2)
