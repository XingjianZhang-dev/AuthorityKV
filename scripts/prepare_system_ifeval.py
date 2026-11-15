#!/usr/bin/env python3
"""Fetch and freeze the public System-IFEval benchmark and its official grader."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import ssl
from collections import Counter, defaultdict
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE_REPOSITORY = "https://github.com/Itisalex2/pitfalls-of-kv-cache-compression"
SOURCE_COMMIT = "73079e1b3bf27cd182f680d7da5edd97b660bd82"
RAW_BASE = (
    "https://raw.githubusercontent.com/Itisalex2/"
    f"pitfalls-of-kv-cache-compression/{SOURCE_COMMIT}/"
)
SOURCE_FILES = {
    "kv_cache_compression/benchmarks/ifeval/inputs/sys_ifeval.jsonl": (
        "1342acbe3979bc54297f504f8fe7449f7456a9c8c1690afaa7346a8dcf8b6fa3"
    ),
    "kv_cache_compression/benchmarks/ifeval/evaluate.py": (
        "b6d2215ed5f4d57438beeec8aa6e543e5dc1e458a53f26486dd46ee7895f8140"
    ),
    "kv_cache_compression/benchmarks/ifeval/utils/__init__.py": (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    ),
    "kv_cache_compression/benchmarks/ifeval/utils/instructions.py": (
        "2ec7c595005a3f0a9ab0ee655c2e374c06af8630f27f6de01c418abd0e2284b9"
    ),
    "kv_cache_compression/benchmarks/ifeval/utils/instructions_registry.py": (
        "13072e317ef9208ec55ab36aef4df159ea8674085e6b0df78f0f5b6b99e02b31"
    ),
    "kv_cache_compression/benchmarks/ifeval/utils/instructions_util.py": (
        "cdbc54d7cfafc822924ea7b71040a4bd0b1fa9600227b8808c09279b5237b021"
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        default=str(ROOT / "data/external_system_ifeval"),
    )
    parser.add_argument(
        "--external-dir",
        default=str(ROOT / "external/system_ifeval"),
    )
    parser.add_argument("--subset-size", type=int, default=150)
    parser.add_argument("--subset-seed", type=int, default=20260726)
    parser.add_argument(
        "--source-root",
        default=None,
        help=(
            "Optional checkout of the pinned source repository. Files are still "
            "verified against the registered SHA-256 values."
        ),
    )
    return parser.parse_args()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def fetch(
    relative_path: str,
    expected_sha256: str,
    source_root: Path | None = None,
) -> bytes:
    if source_root is not None:
        payload = (source_root / relative_path).read_bytes()
    else:
        try:
            import certifi

            ssl_context = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            ssl_context = ssl.create_default_context()
        with urllib.request.urlopen(
            RAW_BASE + relative_path,
            timeout=120,
            context=ssl_context,
        ) as response:
            payload = response.read()
    actual = sha256_bytes(payload)
    if actual != expected_sha256:
        raise RuntimeError(
            f"source hash mismatch for {relative_path}: {actual} != {expected_sha256}"
        )
    return payload


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    payload = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows
    ).encode("utf-8")
    atomic_write(path, payload)


def stratified_subset(
    rows: list[dict[str, Any]],
    *,
    size: int,
    seed: int,
) -> list[dict[str, Any]]:
    """Select a frozen family-balanced subset without using model outcomes."""

    if not 1 <= size <= len(rows):
        raise ValueError("subset size must be between 1 and the dataset size")
    family_counts = Counter(
        instruction_id.split(":", 1)[0]
        for row in rows
        for instruction_id in row["instruction_id_list"]
    )
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        families = {
            instruction_id.split(":", 1)[0]
            for instruction_id in row["instruction_id_list"]
        }
        bucket = min(families, key=lambda family: (family_counts[family], family))
        buckets[bucket].append(row)
    for family in buckets:
        buckets[family].sort(
            key=lambda row: hashlib.sha256(
                f"{seed}\0{row['key']}".encode("utf-8")
            ).hexdigest()
        )

    selected: list[dict[str, Any]] = []
    families = sorted(buckets)
    while len(selected) < size:
        progress = False
        for family in families:
            if buckets[family] and len(selected) < size:
                selected.append(buckets[family].pop())
                progress = True
        if not progress:
            break
    if len(selected) != size:
        raise RuntimeError(f"selected {len(selected)} rows, expected {size}")
    return sorted(selected, key=lambda row: int(row["key"]))


def main() -> None:
    args = parse_args()
    data_dir = Path(args.data_dir)
    external_dir = Path(args.external_dir)
    source_root = Path(args.source_root) if args.source_root else None

    downloaded = {
        relative: fetch(relative, digest, source_root)
        for relative, digest in SOURCE_FILES.items()
    }
    dataset_relative = (
        "kv_cache_compression/benchmarks/ifeval/inputs/sys_ifeval.jsonl"
    )
    source_rows = [
        json.loads(line)
        for line in downloaded[dataset_relative].decode("utf-8").splitlines()
        if line.strip()
    ]
    if len(source_rows) != 539:
        raise RuntimeError(f"expected 539 System-IFEval rows, found {len(source_rows)}")
    subset_source_rows = stratified_subset(
        source_rows,
        size=args.subset_size,
        seed=args.subset_seed,
    )

    generation_rows: list[dict[str, Any]] = []
    label_rows: list[dict[str, Any]] = []
    for row in source_rows:
        key = int(row["key"])
        example_id = f"system_ifeval_{key}"
        messages = row["messages"]
        if [message["role"] for message in messages] != ["system", "user"]:
            raise RuntimeError(f"unexpected message roles for key {key}")
        generation_rows.append(
            {
                "id": example_id,
                "category": "external_system_ifeval",
                "messages": messages,
                "metadata": {
                    "source_key": key,
                    "source_name": "System-IFEval",
                    "source_commit": SOURCE_COMMIT,
                },
            }
        )
        label_rows.append(
            {
                "id": example_id,
                "key": key,
                "instruction_id_list": row["instruction_id_list"],
                "kwargs": row["kwargs"],
                "messages": messages,
            }
        )
    subset_ids = {
        f"system_ifeval_{int(row['key'])}" for row in subset_source_rows
    }
    generation_subset = [
        row for row in generation_rows if row["id"] in subset_ids
    ]
    labels_subset = [row for row in label_rows if row["id"] in subset_ids]

    data_dir.mkdir(parents=True, exist_ok=True)
    atomic_write(data_dir / "sys_ifeval_source.jsonl", downloaded[dataset_relative])
    write_jsonl(data_dir / "sys_ifeval_messages.jsonl", generation_rows)
    write_jsonl(data_dir / "sys_ifeval_labels.jsonl", label_rows)
    write_jsonl(
        data_dir / f"sys_ifeval_messages_{args.subset_size}.jsonl",
        generation_subset,
    )
    write_jsonl(
        data_dir / f"sys_ifeval_labels_{args.subset_size}.jsonl",
        labels_subset,
    )

    package_root = external_dir / "ifeval"
    atomic_write(package_root / "__init__.py", b"")
    for relative, payload in downloaded.items():
        if relative == dataset_relative:
            continue
        suffix = relative.split("benchmarks/ifeval/", 1)[1]
        atomic_write(package_root / suffix, payload)

    source_manifest = {
        "name": "System-IFEval from The Pitfalls of KV Cache Compression",
        "repository": SOURCE_REPOSITORY,
        "commit": SOURCE_COMMIT,
        "retrieved_files": SOURCE_FILES,
        "dataset_license": "CC BY 4.0 (repository declaration)",
        "grader_license": "Apache-2.0 (Google Research file headers)",
        "generation_rows": len(generation_rows),
        "frozen_subset": {
            "rows": args.subset_size,
            "seed": args.subset_seed,
            "selection": (
                "round-robin over the rarest instruction family represented by "
                "each row, with seeded SHA-256 ordering inside family buckets"
            ),
            "keys": sorted(int(row["key"]) for row in subset_source_rows),
        },
        "label_isolation": (
            "The generation file contains only messages and source identifiers. "
            "Instruction IDs and grader kwargs are stored in a separate labels file "
            "read only after generation."
        ),
        "generated_sha256": {
            "sys_ifeval_source.jsonl": sha256_bytes(
                (data_dir / "sys_ifeval_source.jsonl").read_bytes()
            ),
            "sys_ifeval_messages.jsonl": sha256_bytes(
                (data_dir / "sys_ifeval_messages.jsonl").read_bytes()
            ),
            "sys_ifeval_labels.jsonl": sha256_bytes(
                (data_dir / "sys_ifeval_labels.jsonl").read_bytes()
            ),
            f"sys_ifeval_messages_{args.subset_size}.jsonl": sha256_bytes(
                (
                    data_dir
                    / f"sys_ifeval_messages_{args.subset_size}.jsonl"
                ).read_bytes()
            ),
            f"sys_ifeval_labels_{args.subset_size}.jsonl": sha256_bytes(
                (
                    data_dir / f"sys_ifeval_labels_{args.subset_size}.jsonl"
                ).read_bytes()
            ),
        },
    }
    atomic_write(
        external_dir / "SOURCE.json",
        (json.dumps(source_manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    print(json.dumps(source_manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
