#!/usr/bin/env python3
"""Convert NVIDIA/RULER generated JSONL files to AuthorityKV utility JSONL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ruler-root", required=True, help="Directory containing task/validation.jsonl files.")
    parser.add_argument("--tasks", default="niah_single_1,vt")
    parser.add_argument("--out", required=True)
    parser.add_argument("--ruler-repo", default="external/RULER")
    parser.add_argument("--ruler-commit", default=None)
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def main() -> None:
    args = parse_args()
    ruler_root = Path(args.ruler_root)
    tasks = [task.strip() for task in args.tasks.split(",") if task.strip()]
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8") as out_f:
        for task in tasks:
            task_path = ruler_root / task / "validation.jsonl"
            for row in load_jsonl(task_path):
                converted = {
                    "id": f"ruler_official_{task}_{row['index']}",
                    "source": "nvidia_ruler_official",
                    "task": f"ruler_official_{task}",
                    "prompt": row["input"],
                    "answers": row.get("outputs", []),
                    "metadata": {
                        "benchmark": "NVIDIA/RULER",
                        "official_ruler_generated": True,
                        "ruler_task": task,
                        "ruler_index": row["index"],
                        "ruler_length": row.get("length"),
                        "ruler_length_w_model_temp": row.get("length_w_model_temp"),
                        "ruler_answer_prefix": row.get("answer_prefix"),
                        "ruler_repo": args.ruler_repo,
                        "ruler_commit": args.ruler_commit,
                        "utility_judge": "ruler_string_match_all",
                    },
                }
                out_f.write(json.dumps(converted, ensure_ascii=False, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
