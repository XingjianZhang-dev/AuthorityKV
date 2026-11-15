#!/usr/bin/env python3
"""Reconstruct a conservative GPU-compute inventory from saved run configs."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results/authoritykv"
DEFAULT_SNAPSHOT = ROOT / "reports/COMPUTE_INVENTORY_SOURCE.json"


def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def read_exit_code(run_dir: Path) -> int | None:
    for name in ("runner_exit_code.txt", "generation_exit_code.txt"):
        path = run_dir / name
        if not path.exists():
            continue
        try:
            return int(path.read_text().strip())
        except ValueError:
            return None
    return None


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def path_identifier(path: Path) -> str:
    """Return a stable opaque identifier without exposing legacy run names."""
    relative = str(path.relative_to(ROOT)).encode("utf-8")
    return hashlib.sha256(relative).hexdigest()


def load_rows() -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    rows: list[dict[str, Any]] = []
    excluded: list[dict[str, str]] = []
    for path in sorted(RESULTS.rglob("run_config.json")):
        try:
            config = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            excluded.append(
                {
                    "config_id": path_identifier(path),
                    "reason": f"unreadable config: {exc}",
                }
            )
            continue
        start = parse_time(config.get("start_time"))
        end = parse_time(config.get("end_time"))
        if start is None or end is None or end < start:
            excluded.append(
                {
                    "config_sha256": file_sha256(path),
                    "reason": "missing or invalid start/end timestamp",
                }
            )
            continue
        duration_h = (end - start).total_seconds() / 3600.0
        rows.append(
            {
                "config_sha256": file_sha256(path),
                "model": str(config.get("model") or "unknown"),
                "gpu": str(config.get("gpu") or "unrecorded"),
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
                "duration_hours": duration_h,
                "runner_exit_code": read_exit_code(path.parent),
            }
        )
    return rows, excluded


def load_snapshot(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return [], []
    rows = payload.get("runs")
    excluded = payload.get("excluded")
    if not isinstance(rows, list) or not isinstance(excluded, list):
        return [], []
    required = {
        "config_sha256",
        "model",
        "gpu",
        "start_time",
        "end_time",
        "duration_hours",
        "runner_exit_code",
    }
    if any(not isinstance(row, dict) or not required.issubset(row) for row in rows):
        return [], []
    if any(not isinstance(row, dict) for row in excluded):
        return [], []
    return rows, excluded


def write_snapshot(
    path: Path,
    rows: list[dict[str, Any]],
    excluded: list[dict[str, str]],
) -> None:
    payload = {
        "schema_version": 1,
        "description": (
            "Anonymized run-timing ledger used to reconstruct the compute "
            "inventory when the full experiment tree is not distributed."
        ),
        "runs": rows,
        "excluded": excluded,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def aggregate(rows: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {"runs": 0, "hours": 0.0}
    )
    for row in rows:
        key = str(row[field])
        groups[key]["runs"] = int(groups[key]["runs"]) + 1
        groups[key]["hours"] = float(groups[key]["hours"]) + float(
            row["duration_hours"]
        )
    return [
        {
            field: key,
            "runs": int(value["runs"]),
            "process_gpu_hours": round(float(value["hours"]), 6),
        }
        for key, value in sorted(
            groups.items(), key=lambda item: (-float(item[1]["hours"]), item[0])
        )
    ]


def write_markdown(report: dict[str, Any], out: Path) -> None:
    lines = [
        "# GPU compute inventory",
        "",
        f"Generated: {report['generated_at']}",
        "",
        "This is a conservative reconstruction from saved `run_config.json`",
        "start/end timestamps. It counts process-GPU wall time for every",
        "timestamp-complete run, including pilots, negative results, invalidated",
        "runs, and reruns. It does not infer time for configs lacking timestamps.",
        "",
        "## Headline",
        "",
        f"- Timestamp-complete GPU runs: {report['timestamp_complete_runs']}",
        f"- Reconstructed process-GPU hours: {report['process_gpu_hours']:.3f}",
        f"- Configs excluded for missing/invalid timestamps: {report['excluded_configs']}",
        f"- Nonzero recorded runner exits among measured runs: {report['nonzero_exit_runs']}",
        "",
        "The total is suitable as a transparent lower bound for the Responsible",
        "NLP checklist. Concurrent processes are counted separately because each",
        "consumed GPU resources; elapsed node wall time would be smaller.",
        "",
        "## By model",
        "",
        "| Model | Runs | Process-GPU hours |",
        "|---|---:|---:|",
    ]
    for row in report["by_model"]:
        lines.append(
            f"| `{row['model']}` | {row['runs']} | "
            f"{row['process_gpu_hours']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## By recorded GPU",
            "",
            "| GPU | Runs | Process-GPU hours |",
            "|---|---:|---:|",
        ]
    )
    for row in report["by_gpu"]:
        lines.append(
            f"| `{row['gpu']}` | {row['runs']} | "
            f"{row['process_gpu_hours']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This inventory measures completed run durations, not theoretical",
            "  FLOPs or energy.",
            "- It deliberately includes unsuccessful branches so compute is not",
            "  understated by reporting only promoted positive results.",
            "- Public model pretraining and upstream benchmark construction are",
            "  outside the project-compute boundary.",
            "- The machine-readable report lists every measured and excluded run.",
            "",
        ]
    )
    out.write_text("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--json-out",
        type=Path,
        default=ROOT / "reports/COMPUTE_INVENTORY.json",
    )
    parser.add_argument(
        "--md-out",
        type=Path,
        default=ROOT / "reports/COMPUTE_INVENTORY.md",
    )
    parser.add_argument(
        "--source-snapshot",
        type=Path,
        default=DEFAULT_SNAPSHOT,
        help=(
            "anonymized timing ledger; used when it covers more runs than the "
            "locally distributed result tree"
        ),
    )
    args = parser.parse_args()

    live_rows, live_excluded = load_rows()
    snapshot_rows, snapshot_excluded = load_snapshot(args.source_snapshot)
    if len(snapshot_rows) > len(live_rows):
        rows, excluded = snapshot_rows, snapshot_excluded
        data_source = "anonymized timing ledger"
    else:
        rows, excluded = live_rows, live_excluded
        data_source = "saved run configurations"
        write_snapshot(args.source_snapshot, rows, excluded)
    nonzero = sum(
        row["runner_exit_code"] not in (None, 0) for row in rows
    )
    report = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "scope": "saved AuthorityKV GPU run configurations",
        "data_source": data_source,
        "method": "sum of nonnegative end_time - start_time durations",
        "timestamp_complete_runs": len(rows),
        "process_gpu_hours": round(
            sum(float(row["duration_hours"]) for row in rows), 6
        ),
        "excluded_configs": len(excluded),
        "nonzero_exit_runs": nonzero,
        "by_model": aggregate(rows, "model"),
        "by_gpu": aggregate(rows, "gpu"),
        "runs": rows,
        "excluded": excluded,
    }
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    write_markdown(report, args.md_out)
    print(
        json.dumps(
            {
                "timestamp_complete_runs": report["timestamp_complete_runs"],
                "process_gpu_hours": report["process_gpu_hours"],
                "excluded_configs": report["excluded_configs"],
                "nonzero_exit_runs": report["nonzero_exit_runs"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
