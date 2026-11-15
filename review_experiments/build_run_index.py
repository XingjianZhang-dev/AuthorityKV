#!/usr/bin/env python3
"""Write results/RUN_INDEX.csv: one row per released run (main matrix and review-period experiments).

Reads only the run configurations, so it works on a fresh clone. When the raw-output archives are
extracted at the repository root, the number of stored predictions per run is filled in as well."""
from __future__ import annotations

import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FIELDS = ["run", "group", "experiment", "model", "task_or_dataset", "scorers_or_methods", "keep_ratios", "tie_rule", "predictions", "archive"]
TIE = {"topk": "R-up (torch.topk)", "recency": "R-down (recency)", "earliest": "R-up (explicit sort)", "random": "random (seeded)"}


def n_lines(path: Path) -> str:
    if not path.exists():
        return ""
    with path.open("rb") as handle:
        return str(sum(1 for _ in handle))


def ratios(values) -> str:
    if values in (None, ""):
        return ""
    if isinstance(values, str):
        values = values.replace(",", " ").split()
    if not isinstance(values, (list, tuple)):
        values = [values]
    return " ".join(f"{float(v):g}" for v in values)


def main_rows():
    for cfg in sorted((REPO / "results" / "authoritykv").glob("*/run_config.json")):
        c = json.loads(cfg.read_text(encoding="utf-8"))
        yield {
            "run": cfg.parent.name,
            "group": "main",
            "experiment": cfg.parent.name.split("_")[0],
            "model": c.get("model", ""),
            "task_or_dataset": c.get("dataset", ""),
            "scorers_or_methods": " ".join(c.get("methods") or []),
            "keep_ratios": ratios(c.get("keep_ratios")),
            "tie_rule": TIE["topk"],
            "predictions": n_lines(cfg.parent / "predictions.jsonl"),
            "archive": "authoritykv_main_experiments_predictions.tar.zst",
        }


def review_rows():
    for cfg in sorted((REPO / "runs").glob("*/config.json")):
        c = json.loads(cfg.read_text(encoding="utf-8"))
        h = c.get("hyperparams") or {}
        variants = h.get("variants") or c.get("variant") or ""
        if isinstance(variants, (list, tuple)):
            variants = " ".join(map(str, variants))
        scorer = h.get("scorer") or h.get("scorers") or ""
        if isinstance(scorer, (list, tuple)):
            scorer = " ".join(map(str, scorer))
        yield {
            "run": cfg.parent.name,
            "group": "review",
            "experiment": str(c.get("experiment_id", "")),
            "model": c.get("model", ""),
            "task_or_dataset": h.get("dataset") or h.get("task") or "",
            "scorers_or_methods": " | ".join(x for x in (str(scorer), str(variants)) if x),
            "keep_ratios": ratios(h.get("keep_ratios") or h.get("ratios") or c.get("keep_ratio")),
            "tie_rule": TIE.get(str(c.get("tie_break")), str(c.get("tie_break") or "")),
            "predictions": n_lines(cfg.parent / "predictions.jsonl"),
            "archive": "authoritykv_review_experiments_runs.tar.zst",
        }


def main() -> None:
    rows = list(main_rows()) + list(review_rows())
    out = REPO / "results" / "RUN_INDEX.csv"
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} runs -> {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
