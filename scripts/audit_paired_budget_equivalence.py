#!/usr/bin/env python3
"""Fail-closed audit of per-example budget equivalence for paired KV methods."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BUDGET_FIELDS = (
    "prompt_tokens",
    "retained_prompt_tokens",
    "retained_prompt_tokens_min",
    "retained_prompt_tokens_max",
)
IDENTITY_FIELDS = (
    "model",
    "dataset",
    "example_index",
    "category",
    "expected_behavior",
)
PROTECTED_FRACTION_ABS_TOLERANCE = 1e-6


@dataclass(frozen=True)
class PairSpec:
    name: str
    base_run: str
    base_method: str
    comparison_run: str
    comparison_method: str
    expected_pairs: int


def parse_pair_spec(text: str) -> PairSpec:
    fields = text.split("|")
    if len(fields) != 6:
        raise ValueError(
            "pair spec must be "
            "name|base_run|base_method|comparison_run|comparison_method|expected_pairs"
        )
    expected_pairs = int(fields[5])
    if expected_pairs <= 0 or any(not field for field in fields[:5]):
        raise ValueError(f"invalid pair spec: {text!r}")
    return PairSpec(*fields[:5], expected_pairs)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number}: expected JSON object")
            rows.append(row)
    return rows


def row_key(row: dict[str, Any]) -> tuple[str, float]:
    return str(row["example_id"]), float(row.get("keep_ratio", 1.0))


def index_method(
    rows: list[dict[str, Any]],
    method: str,
) -> tuple[dict[tuple[str, float], dict[str, Any]], int]:
    selected = [row for row in rows if str(row.get("method")) == method]
    indexed = {row_key(row): row for row in selected}
    return indexed, len(selected) - len(indexed)


def audit_pair(results_root: Path, spec: PairSpec) -> dict[str, Any]:
    base_path = results_root / spec.base_run / "predictions.jsonl"
    comparison_path = (
        results_root / spec.comparison_run / "predictions.jsonl"
    )
    failures: list[str] = []
    if not base_path.is_file():
        failures.append(f"missing base predictions: {base_path}")
    if not comparison_path.is_file():
        failures.append(
            f"missing comparison predictions: {comparison_path}"
        )
    if failures:
        return {
            **asdict(spec),
            "status": "FAIL",
            "failures": failures,
        }

    base, base_duplicates = index_method(
        load_jsonl(base_path), spec.base_method
    )
    comparison, comparison_duplicates = index_method(
        load_jsonl(comparison_path), spec.comparison_method
    )
    base_keys = set(base)
    comparison_keys = set(comparison)
    common_keys = sorted(base_keys & comparison_keys)
    missing_base = sorted(comparison_keys - base_keys)
    missing_comparison = sorted(base_keys - comparison_keys)
    field_mismatches = {
        field: sum(
            base[key].get(field) != comparison[key].get(field)
            for key in common_keys
        )
        for field in BUDGET_FIELDS
    }
    identity_mismatches = {
        field: sum(
            base[key].get(field) != comparison[key].get(field)
            for key in common_keys
        )
        for field in IDENTITY_FIELDS
    }
    non_ok_pairs = sum(
        base[key].get("status", "ok") != "ok"
        or comparison[key].get("status", "ok") != "ok"
        or base[key].get("error") is not None
        or comparison[key].get("error") is not None
        for key in common_keys
    )
    runtime_error_pairs = sum(
        base[key].get("status") == "runtime_error"
        or comparison[key].get("status") == "runtime_error"
        or base[key].get("error") is not None
        or comparison[key].get("error") is not None
        for key in common_keys
    )
    comparison_audits = [
        layer
        for key in common_keys
        for layer in comparison[key].get("press_audit", [])
        if isinstance(layer, dict)
    ]
    protected_fraction_values = [
        float(layer["protected_kept_fraction"])
        for layer in comparison_audits
        if layer.get("protected_kept_fraction") is not None
    ]
    protected_fraction_below_one = sum(
        not math.isclose(
            value,
            1.0,
            rel_tol=0.0,
            abs_tol=PROTECTED_FRACTION_ABS_TOLERANCE,
        )
        for value in protected_fraction_values
    )

    if len(common_keys) != spec.expected_pairs:
        failures.append(
            f"expected {spec.expected_pairs} pairs, found {len(common_keys)}"
        )
    if base_duplicates or comparison_duplicates:
        failures.append(
            "duplicate method keys: "
            f"base={base_duplicates}, comparison={comparison_duplicates}"
        )
    if missing_base or missing_comparison:
        failures.append(
            "paired key mismatch: "
            f"missing_base={len(missing_base)}, "
            f"missing_comparison={len(missing_comparison)}"
        )
    for field, count in field_mismatches.items():
        if count:
            failures.append(f"{field} differs for {count} pairs")
    for field, count in identity_mismatches.items():
        if count:
            failures.append(f"identity field {field} differs for {count} pairs")
    if non_ok_pairs:
        failures.append(f"non-ok paired outcomes: {non_ok_pairs}")
    if not comparison_audits:
        failures.append("comparison press_audit is empty")
    if not protected_fraction_values:
        failures.append("protected kept-fraction evidence is missing")
    if protected_fraction_below_one:
        failures.append(
            "protected kept fraction below one for "
            f"{protected_fraction_below_one} layer audits"
        )

    return {
        **asdict(spec),
        "status": "PASS" if not failures else "FAIL",
        "base_rows_for_method": len(base),
        "comparison_rows_for_method": len(comparison),
        "paired_rows": len(common_keys),
        "base_duplicate_keys": base_duplicates,
        "comparison_duplicate_keys": comparison_duplicates,
        "missing_base_keys": len(missing_base),
        "missing_comparison_keys": len(missing_comparison),
        "budget_field_mismatches": field_mismatches,
        "identity_field_mismatches": identity_mismatches,
        "non_ok_pairs": non_ok_pairs,
        "runtime_error_pairs": runtime_error_pairs,
        "comparison_layer_audits": len(comparison_audits),
        "protected_fraction_observations": len(
            protected_fraction_values
        ),
        "protected_fraction_abs_tolerance": (
            PROTECTED_FRACTION_ABS_TOLERANCE
        ),
        "protected_fraction_below_one": protected_fraction_below_one,
        "failures": failures,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results-root",
        default="results/authoritykv",
    )
    parser.add_argument(
        "--pair",
        action="append",
        required=True,
        help=(
            "name|base_run|base_method|comparison_run|"
            "comparison_method|expected_pairs"
        ),
    )
    parser.add_argument(
        "--out",
        default="reports/paired_budget_equivalence_audit.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    specs = [parse_pair_spec(text) for text in args.pair]
    names = [spec.name for spec in specs]
    identities = [
        (
            spec.base_run,
            spec.base_method,
            spec.comparison_run,
            spec.comparison_method,
            spec.expected_pairs,
        )
        for spec in specs
    ]
    duplicate_names = sorted(
        {name for name in names if names.count(name) > 1}
    )
    duplicate_identities = sorted(
        {
            identity
            for identity in identities
            if identities.count(identity) > 1
        }
    )
    results_root = Path(args.results_root)
    pair_reports = [audit_pair(results_root, spec) for spec in specs]
    passed = (
        bool(pair_reports)
        and not duplicate_names
        and not duplicate_identities
        and all(
        report["status"] == "PASS" for report in pair_reports
        )
    )
    payload = {
        "status": "PASS" if passed else "FAIL",
        "audited_at_utc": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ),
        "budget_fields": list(BUDGET_FIELDS),
        "identity_fields": list(IDENTITY_FIELDS),
        "duplicate_spec_names": duplicate_names,
        "duplicate_spec_identities": [
            list(identity) for identity in duplicate_identities
        ],
        "pairs": pair_reports,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "out": str(out),
                "pair_count": len(pair_reports),
            },
            sort_keys=True,
        )
    )
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
