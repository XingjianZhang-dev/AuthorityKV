#!/usr/bin/env python3
"""Create a paired native-system variant of an adapted IH-Challenge JSONL."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    return parser.parse_args()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    out_path = Path(args.out)
    rows: list[dict[str, Any]] = [
        json.loads(line)
        for line in input_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    input_hash = sha256(input_path)
    transformed: list[dict[str, Any]] = []
    for row in rows:
        messages = row.get("messages", [])
        original_roles = [str(message.get("role", "")) for message in messages]
        if "developer" not in original_roles:
            raise RuntimeError(
                f"{row.get('id')}: expected at least one developer message"
            )
        mapped_messages = [
            {
                **message,
                "role": (
                    "system"
                    if str(message.get("role", "")).lower() == "developer"
                    else str(message.get("role", ""))
                ),
            }
            for message in messages
        ]
        metadata = dict(row.get("metadata", {}))
        metadata.update(
            {
                "source_dataset": str(input_path),
                "source_dataset_sha256": input_hash,
                "original_chat_roles": original_roles,
                "rendered_control_role": "system",
                "role_mapping_note": (
                    "The source IH-Challenge developer control message is "
                    "mapped to the model-native system role. Message contents, "
                    "user attack text, example IDs, and official grader code "
                    "are otherwise byte-identical to the paired source row."
                ),
            }
        )
        transformed.append(
            {
                **row,
                "messages": mapped_messages,
                "metadata": metadata,
            }
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for row in transformed:
            handle.write(
                json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            )
    print(json.dumps(
        {
            "input": str(input_path),
            "input_sha256": input_hash,
            "out": str(out_path),
            "rows": len(transformed),
            "out_sha256": sha256(out_path),
        },
        indent=2,
    ))


if __name__ == "__main__":
    main()
