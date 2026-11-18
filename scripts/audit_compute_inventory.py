#!/usr/bin/env python3
"""Reconstruct the GPU-compute inventory of all experiments from the timestamps saved with each run.

Two groups are counted: the main experiments (`results/authoritykv/<run>/run_config.json`) and the
extended experiments (`runs/<run>/config.json`). The total is the figure reported in Appendix F.8.
"""

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
EXTENDED = ROOT / "runs"
PAPER_MODELS = {
    "Qwen/Qwen2.5-7B-Instruct",
    "mistralai/Mistral-7B-Instruct-v0.3",
    "01-ai/Yi-1.5-9B-Chat",
    "Qwen/Qwen2.5-14B-Instruct",
}
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


def load_extended_rows() -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """One row per run directory under runs/, from its config.json (run_config.json if absent)."""
    rows: list[dict[str, Any]] = []
    excluded: list[dict[str, str]] = []
    for run_dir in sorted(p for p in EXTENDED.iterdir() if p.is_dir()):
        path = run_dir / "config.json"
        if not path.exists():
            path = run_dir / "run_config.json"
        if not path.exists():
            continue  # helper directories without a run (e.g. id lists)
        try:
            config = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            excluded.append({"config_id": path_identifier(path), "reason": f"unreadable config: {exc}"})
            continue
        start = parse_time(config.get("start_time"))
        end = parse_time(config.get("end_time"))
        if start is None or end is None or end < start:
            excluded.append(
                {"config_sha256": file_sha256(path), "reason": "missing or invalid start/end timestamp"}
            )
            continue
        environment = config.get("environment") if isinstance(config.get("environment"), dict) else {}
        rows.append(
            {
                "config_sha256": file_sha256(path),
                "model": str(config.get("model") or "unknown"),
                "gpu": str(environment.get("gpu") or config.get("gpu") or "unrecorded"),
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
                "duration_hours": (end - start).total_seconds() / 3600.0,
                "runner_exit_code": read_exit_code(run_dir),
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
    main, ext = report["groups"]["main"], report["groups"]["extended"]
    lines = [
        "# GPU compute inventory",
        "",
        "Process-GPU wall time of every experiment, reconstructed from the start and end timestamps saved",
        "with each run configuration (`python scripts/audit_compute_inventory.py` rebuilds this file and",
        "`COMPUTE_INVENTORY.json`).",
        "",
        "## Headline",
        "",
        f"- Process-GPU hours, all experiments: {report['process_gpu_hours']:.1f}",
        f"- Main experiments (`results/authoritykv/`): {main['process_gpu_hours']:.1f} hours over "
        f"{main['timestamp_complete_runs']} run configurations",
        f"- Extended experiments (`runs/`): {ext['process_gpu_hours']:.1f} hours over "
        f"{ext['timestamp_complete_runs']} runs",
        f"- Configurations without complete timestamps, not counted: {report['excluded_configs']}",
        "",
        "Every timestamp-complete configuration is counted, so the total is a lower bound on project",
        "compute. Concurrent processes are counted separately; elapsed node time is smaller.",
        "",
        "## By model",
        "",
        "| Model | Runs | Process-GPU hours |",
        "|---|---:|---:|",
    ]
    other_runs, other_hours = 0, 0.0
    for row in report["by_model"]:
        if row["model"] in PAPER_MODELS:
            lines.append(f"| `{row['model']}` | {row['runs']} | {row['process_gpu_hours']:.3f} |")
        else:
            other_runs += int(row["runs"])
            other_hours += float(row["process_gpu_hours"])
    if other_runs:
        lines.append(f"| Smoke tests, audits, and detector probes | {other_runs} | {other_hours:.3f} |")
    lines.extend(["", "## By recorded GPU", "", "| GPU | Runs | Process-GPU hours |", "|---|---:|---:|"])
    for row in report["by_gpu"]:
        lines.append(f"| `{row['gpu']}` | {row['runs']} | {row['process_gpu_hours']:.3f} |")
    lines.extend(
        [
            "",
            "## Scope",
            "",
            "- The inventory measures run durations, not FLOPs or energy.",
            "- Public model pretraining and upstream benchmark construction are outside the project-compute",
            "  boundary.",
            "- `COMPUTE_INVENTORY.json` lists every counted and excluded configuration with its group.",
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
    ext_rows, ext_excluded = load_extended_rows()
    for row in rows:
        row["group"] = "main"
    for row in excluded:
        row["group"] = "main"
    for row in ext_rows:
        row["group"] = "extended"
    for row in ext_excluded:
        row["group"] = "extended"
    all_rows = rows + ext_rows
    all_excluded = excluded + ext_excluded

    def group_summary(group_rows: list[dict[str, Any]], group_excluded: list[dict[str, str]], source: str) -> dict[str, Any]:
        return {
            "data_source": source,
            "timestamp_complete_runs": len(group_rows),
            "process_gpu_hours": round(sum(float(row["duration_hours"]) for row in group_rows), 6),
            "excluded_configs": len(group_excluded),
        }

    report = {
        "scope": "GPU run configurations of the main and extended AuthorityKV experiments",
        "method": "sum of nonnegative end_time - start_time durations",
        "latest_run_end": max(row["end_time"] for row in all_rows),
        "timestamp_complete_runs": len(all_rows),
        "process_gpu_hours": round(sum(float(row["duration_hours"]) for row in all_rows), 6),
        "excluded_configs": len(all_excluded),
        "nonzero_exit_runs": sum(row["runner_exit_code"] not in (None, 0) for row in all_rows),
        "groups": {
            "main": group_summary(rows, excluded, data_source),
            "extended": group_summary(ext_rows, ext_excluded, "saved run configurations under runs/"),
        },
        "by_model": aggregate(all_rows, "model"),
        "by_gpu": aggregate(all_rows, "gpu"),
        "runs": all_rows,
        "excluded": all_excluded,
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
