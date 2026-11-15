#!/usr/bin/env python3
"""Create a deterministic category-stratified JSONL subset."""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--per-category", type=int, required=True)
    parser.add_argument("--seed", type=int, default=20260725)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = [
        json.loads(line)
        for line in Path(args.input).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("category", "unknown"))].append(row)

    rng = random.Random(args.seed)
    selected = []
    counts = {}
    for category in sorted(grouped):
        candidates = grouped[category][:]
        rng.shuffle(candidates)
        category_rows = candidates[: args.per_category]
        selected.extend(category_rows)
        counts[category] = len(category_rows)

    rng.shuffle(selected)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in selected:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(
        json.dumps(
            {
                "input": args.input,
                "output": args.output,
                "rows": len(selected),
                "counts": counts,
                "seed": args.seed,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
