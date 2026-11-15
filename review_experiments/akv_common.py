"""Shared helpers for the review-period experiments: load the frozen runners by import and write a config.json per run.

Nothing here modifies frozen code. Two runner versions exist:
  snapshot = repro_snapshots/acl_parent_20260725/scripts/run_kvpress_authority.py (sha 314d5927; detector on all
             annotated spans; strict policy only)  -> IH-CacheBench family
  current  = scripts/run_kvpress_authority.py (sha 2479b473; detector on chat spans only; priority policy,
             dropout/shrink, --scan-low-authority-chat) -> mixed-evidence / System-IFEval family
Only one version can be loaded per process (module name `run_authoritykv_smoke` is shared).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
SNAPSHOT_ROOT = REPO / "repro_snapshots" / "acl_parent_20260725"
RUNS_DIR = REPO / "runs"

EXPECTED_SHA = {
    "snapshot": {
        "scripts/run_kvpress_authority.py": "314d59271712b001e460d6e364207272dfe3600015a59fbef9daf4915790ef0c",
        "authoritykv_experiments/kvpress_authority.py": "870995d2cc792d597fc9130477bde4fb7ff8f619e278d3807d4a3c4b83401199",
        "scripts/run_authoritykv_smoke.py": "391aec0542936007810f28c4902a7c496c814c1a2cdd9299bfee9b4f02e20dc3",
    },
    "current": {
        "scripts/run_kvpress_authority.py": "2479b473a5a5d5d44268abe0ef546c6c862d57c2646ebd1266a30db96d3548f2",
        "authoritykv_experiments/kvpress_authority.py": "a4af6dc84f9440a694decaab73e9ccedea1a46d58d7b1a0edd3146e9d62c8433",
        "scripts/run_authoritykv_smoke.py": "8faa998ace07913fc0bd64bbd8e50519e352da9a4eb22f02ff6d798da98f1930",
    },
}
DETECTOR_INPUT_SCOPE = {
    "snapshot": "all_annotated_spans (metadata_marker + chat spans; whole span demoted on hit)",
    "current": "chat_message spans only (sentence-level localisation when --scan-low-authority-chat)",
}

_LOADED_VERSION: str | None = None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def runner_root(version: str) -> Path:
    if version == "snapshot":
        return SNAPSHOT_ROOT
    if version == "current":
        return REPO
    raise ValueError(f"unknown runner version: {version}")


def verify_runner_sources(version: str) -> dict[str, str]:
    root = runner_root(version)
    hashes = {}
    for rel, expected in EXPECTED_SHA[version].items():
        actual = sha256_file(root / rel)
        if actual != expected:
            raise RuntimeError(f"frozen source hash mismatch for {version}:{rel}: {actual} != {expected}")
        hashes[str(root.relative_to(REPO) / rel) if root != REPO else rel] = actual
    return hashes


def load_runner(version: str) -> types.ModuleType:
    """Import the frozen runner module of the requested version without modifying it."""

    global _LOADED_VERSION
    if _LOADED_VERSION is not None and _LOADED_VERSION != version:
        raise RuntimeError(f"runner version {_LOADED_VERSION} already loaded in this process")
    verify_runner_sources(version)
    root = runner_root(version)
    if version == "snapshot":
        if "run_authoritykv_smoke" in sys.modules or "authoritykv_experiments" in sys.modules:
            raise RuntimeError("current-tree modules already imported; cannot load snapshot runner")
        # The snapshot directory has no authoritykv_experiments/__init__.py, so build the package by hand from the
        # snapshot's kvpress_authority.py (sha 870995d2) and expose the four names the runner imports.
        pkg = types.ModuleType("authoritykv_experiments")
        pkg.__path__ = [str(root / "authoritykv_experiments")]  # type: ignore[attr-defined]
        spec = importlib.util.spec_from_file_location(
            "authoritykv_experiments.kvpress_authority", root / "authoritykv_experiments" / "kvpress_authority.py"
        )
        assert spec and spec.loader
        wrapper = importlib.util.module_from_spec(spec)
        sys.modules["authoritykv_experiments.kvpress_authority"] = wrapper
        spec.loader.exec_module(wrapper)
        for name in ("AuthorityAwarePress", "InfeasibleBudgetError", "OFFICIAL_PRESS_METHODS", "build_official_press"):
            setattr(pkg, name, getattr(wrapper, name))
        pkg.kvpress_authority = wrapper  # type: ignore[attr-defined]
        sys.modules["authoritykv_experiments"] = pkg
        sys.path.insert(0, str(root / "scripts"))  # `run_authoritykv_smoke` -> snapshot version (391aec05)
    else:
        sys.path.insert(0, str(root / "scripts"))
        sys.path.insert(0, str(root))
    spec = importlib.util.spec_from_file_location(f"frozen_runner_{version}", root / "scripts" / "run_kvpress_authority.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    # Post-load identity checks: the smoke module and wrapper actually bound must be the expected files.
    smoke = sys.modules["run_authoritykv_smoke"]
    if sha256_file(smoke.__file__) != EXPECTED_SHA[version]["scripts/run_authoritykv_smoke.py"]:
        raise RuntimeError(f"bound run_authoritykv_smoke is not the {version} version: {smoke.__file__}")
    wrapper_file = sys.modules["authoritykv_experiments.kvpress_authority"].__file__
    if sha256_file(wrapper_file) != EXPECTED_SHA[version]["authoritykv_experiments/kvpress_authority.py"]:
        raise RuntimeError(f"bound kvpress_authority is not the {version} version: {wrapper_file}")
    _LOADED_VERSION = version
    return module


def kvpress_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(REPO / "external" / "kvpress"), "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        snap = REPO / "env_snapshot" / "kvpress-commit.txt"
        return snap.read_text().strip() if snap.exists() else None


def environment_block() -> dict[str, Any]:
    import torch
    import transformers
    import kvpress

    return {
        "python": sys.version.split()[0],
        "python_bin": sys.executable,
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "kvpress_import_path": kvpress.__file__,
        "kvpress_commit": kvpress_commit(),
        "cuda_runtime": torch.version.cuda,
        "cudnn": torch.backends.cudnn.version(),
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "HF_HOME": os.environ.get("HF_HOME"),
        "HF_HUB_OFFLINE": os.environ.get("HF_HUB_OFFLINE"),
        "NLTK_DATA": os.environ.get("NLTK_DATA"),
        "hostname": os.uname().nodename,
        "pid": os.getpid(),
    }


def base_config(
    *,
    experiment_id: str,
    runner_version: str,
    model: str,
    dtype: str,
    seed: int,
    keep_ratio: float | None,
    variant: str,
    hyperparams: dict[str, Any],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg: dict[str, Any] = {
        "experiment_id": experiment_id,
        "start_time": now_iso(),
        "end_time": None,
        "repo_git_commit": None,
        "repo_git_note": "repository has no .git (docs/INVENTORY.md §0/G5); code identity = source sha256 below",
        "runner_version": runner_version,
        "runner_source_sha256": verify_runner_sources(runner_version),
        "wrapper_source_sha256": EXPECTED_SHA[runner_version]["authoritykv_experiments/kvpress_authority.py"],
        "detector_input_scope": DETECTOR_INPUT_SCOPE[runner_version],
        "tie_break": "topk",
        "model": model,
        "model_revision": None,  # filled from the runner's run_config.json (config._commit_hash) after loading
        "dtype": dtype,
        "decoding": "greedy (argmax), generation-phase KV not compressed",
        "seed": seed,
        "keep_ratio": keep_ratio,
        "budget_rule": "kept_count = max(1, int(cache_length * (1 - compression_ratio))), compression_ratio = 1 - keep_ratio; PyramidKV native allocation",
        "variant": variant,
        "hyperparams": hyperparams,
        "environment": environment_block(),
        "command": " ".join(sys.argv),
    }
    if extra:
        cfg.update(extra)
    return cfg


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def new_run_dir(experiment_id: str, model_tag: str, scorer: str, kv: str) -> Path:
    """runs/<YYYYmmdd-HHMM>_<experimentID>_<model>_<scorer>_<kv>/ ; never reuses an existing directory."""

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    base = f"{stamp}_{experiment_id}_{model_tag}_{scorer}_{kv}"
    path = RUNS_DIR / base
    suffix = 1
    while path.exists():
        suffix += 1
        path = RUNS_DIR / f"{base}-{suffix}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def first_divergence(a: list[int], b: list[int]) -> int | None:
    for index, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return index
    if len(a) != len(b):
        return min(len(a), len(b))
    return None


def load_module_by_path(name: str, path: Path):
    """Import a frozen module (stdlib-only, e.g. the snapshot judge) under an explicit module name."""

    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# (model_tag, task, scorer) -> stored run id whose kvpress_<scorer> rows give the paired base retained counts
PAIRED_BASE = {}
for _s in ("knorm", "streaming", "snapkv", "tova", "pyramid"):
    PAIRED_BASE[("qwen7b", "ih", _s)] = "aclmain_20260725v1_qwen7b_official_nonh2o500"
    PAIRED_BASE[("mistral7b", "ih", _s)] = "aclmain_20260725v1_mistral7b_official_nonh2o500"
    PAIRED_BASE[("yi9b", "ih", _s)] = "aclmain_20260725v1_yi9b_official_nonh2o500"
PAIRED_BASE[("qwen7b", "ih", "h2o")] = "aclmain_20260725v1_qwen7b_h2o_compositions500"
PAIRED_BASE[("mistral7b", "ih", "h2o")] = "aclmain_20260725v1_mistral7b_core_h2o500"
PAIRED_BASE[("yi9b", "ih", "h2o")] = "aclmain_20260725v1_yi9b_core_h2o500"
PAIRED_BASE[("qwen7b", "mixed", "streaming")] = "arrmixed_20260726v4_qwen_streaming_full300"
PAIRED_BASE[("qwen7b", "mixed", "knorm")] = "arrmixed_20260726v4_qwen_knorm40_full300"
PAIRED_BASE[("qwen7b", "sys", "streaming")] = "arrsys_20260726v4_qwen_streaming40_full150"
PAIRED_BASE[("qwen7b", "sys", "knorm")] = "arrsys_20260726v4_qwen_knorm40_full150"
PAIRED_BASE[("qwen7b", "curve", "streaming")] = "aclmain_20260725v1_qwen7b_curve_nonh2o120"
PAIRED_BASE[("qwen7b", "curve", "knorm")] = "aclmain_20260725v1_qwen7b_curve_nonh2o120"
PAIRED_BASE[("qwen7b", "curve", "h2o")] = "aclmain_20260725v1_qwen7b_curve_h2o120"
PAIRED_BASE[("qwen7b", "ihc", "h2o")] = "aclfollow_20260725v2_qwen7b_ih_native_h2o40"
for _s in ("knorm", "streaming", "snapkv", "tova", "pyramid"):
    PAIRED_BASE[("qwen7b", "ihc", _s)] = "aclfollow_20260725v2_qwen7b_ih_native_nonh2o40"

for _surf, _tag in (("paraphrase", "paraphrase"), ("display_label", "display"), ("option_card", "option")):
    for _s in ("knorm", "streaming"):
        PAIRED_BASE[("qwen7b", f"heldout_{_surf}", _s)] = f"aclmain_20260725v1_qwen7b_heldout_{_tag}_nonh2o120"
    PAIRED_BASE[("qwen7b", f"heldout_{_surf}", "h2o")] = f"aclmain_20260725v1_qwen7b_heldout_{_tag}_h2o120"
