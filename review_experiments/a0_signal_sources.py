#!/usr/bin/env python3
"""A0 — signal-source audit (EXPERIMENTS §2 A0; CPU only). Writes results/A0_signal_sources.md and a run dir with
summary.json. Every claim is derived here: (i) static scan of readers of per-example fields and call chains;
(ii) detector-v3 constants + version diff; (iii) P/D provenance aggregated from stored predictions; (iv) counterfactual
mutation of per-example fields (P/D recomputed with the frozen span/detector/provenance functions); (v) provenance
dropout tier; (vi) 8k correct/wrong arms.
"""

from __future__ import annotations

import collections
import importlib.util
import inspect
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import akv_common as C  # noqa: E402

RES = C.REPO / "results" / "authoritykv"
FIELDS = [
    "conflict_triggers", "high_location", "conflict_style", "is_benign", "expected_behavior", "judge_rule",
    "low_authority_conflict", "high_authority_instruction", "attack_marker", "pair_id", "global_index",
    "_high_", "_low_", "_extra_", "span_id", "start_marker", "end_marker",
]
KVPRESS_PATH_FILES = [
    "scripts/run_kvpress_authority.py",
    "repro_snapshots/acl_parent_20260725/scripts/run_kvpress_authority.py",
    "scripts/run_kvpress_ih_challenge.py",
    "scripts/run_outcome_informed_authority.py",
    "scripts/run_kvpress_external_utility.py",
    "scripts/run_authoritykv_smoke.py",
    "repro_snapshots/acl_parent_20260725/scripts/run_authoritykv_smoke.py",
    "authoritykv_experiments/kvpress_authority.py",
    "repro_snapshots/acl_parent_20260725/authoritykv_experiments/kvpress_authority.py",
    "authoritykv_experiments/outcome_informed_authority.py",
]


def grep_lines(path: Path, needle: str) -> list[int]:
    return [i + 1 for i, line in enumerate(path.read_text(errors="replace").splitlines()) if needle in line]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    out = C.new_run_dir("A0", "qwen7b", "none", "na")
    cfg = C.base_config(experiment_id="A0", runner_version="current", model="Qwen/Qwen2.5-7B-Instruct (tokenizer only, CPU)", dtype="n/a", seed=0,
                        keep_ratio=None, variant="signal_source_audit", hyperparams={"fields": FIELDS, "files": KVPRESS_PATH_FILES})
    C.write_json(out / "config.json", cfg)
    S: dict = {"valid": True}

    # ---------- (i) static scan ----------
    static = {}
    for rel in KVPRESS_PATH_FILES:
        p = C.REPO / rel
        static[rel] = {f: grep_lines(p, f) for f in FIELDS}
        static[rel]["has_conflict_calls"] = [n for n in grep_lines(p, "has_conflict(") if "def has_conflict" not in p.read_text().splitlines()[n - 1]]
        static[rel]["sha256_8"] = C.sha256_file(p)[:8]
    # who calls has_conflict anywhere
    callers = {}
    for p in list((C.REPO / "scripts").glob("*.py")) + list((C.REPO / "repro_snapshots").rglob("*.py")) + list((C.REPO / "authoritykv_experiments").glob("*.py")):
        ls = [n for n in grep_lines(p, "has_conflict(") if "def has_conflict" not in p.read_text().splitlines()[n - 1]]
        if ls:
            callers[str(p.relative_to(C.REPO))] = ls
    S["static"] = {"per_file": static, "has_conflict_callers": callers}
    # key code locations (line numbers computed, not hand-typed)
    cur_runner = C.REPO / "scripts/run_kvpress_authority.py"
    snap_runner = C.SNAPSHOT_ROOT / "scripts/run_kvpress_authority.py"
    cur_smoke = C.REPO / "scripts/run_authoritykv_smoke.py"
    snap_smoke = C.SNAPSHOT_ROOT / "scripts/run_authoritykv_smoke.py"
    loc = {
        "cur_runner.protected_levels_default": grep_lines(cur_runner, 'protected_levels = {"system", "developer"}'),
        "snap_runner.protected_levels_default": grep_lines(snap_runner, 'protected_levels = {"system", "developer"}'),
        "cur_runner.detector_call": grep_lines(cur_runner, "detected_low_authority_token_set("),
        "snap_runner.detector_call": grep_lines(snap_runner, "detected_low_authority_token_set("),
        "cur_runner.detector_spans_chat_only": grep_lines(cur_runner, 'span.get("source") == "chat_message"'),
        "cur_runner.provenance_call": grep_lines(cur_runner, "untrusted_observation_token_set("),
        "snap_runner.provenance_call": grep_lines(snap_runner, "untrusted_observation_token_set("),
        "cur_runner.perturb_metadata_spans_def": grep_lines(cur_runner, "def perturb_metadata_spans"),
        "cur_runner.perturb_continue": grep_lines(cur_runner, "if draw < drop_rate:"),
        "cur_smoke.find_token_spans_def": grep_lines(cur_smoke, "def find_token_spans"),
        "cur_smoke.find_token_spans_role_filter": grep_lines(cur_smoke, "if role not in CHAT_HIGH_AUTHORITY_ROLES"),
        "cur_smoke.find_token_spans_metadata_loop": grep_lines(cur_smoke, 'for span in example.get("metadata", {}).get("authority_spans", [])'),
        "cur_smoke.span_is_untrusted_observation_def": grep_lines(cur_smoke, "def span_is_untrusted_observation"),
        "cur_smoke.span_is_untrusted_observation_text_join": grep_lines(cur_smoke, 'for key in ("span_id", "start_marker", "end_marker", "text")'),
        "cur_smoke.retrieved_document_true": grep_lines(cur_smoke, 'if level == "retrieved_document":'),
        "cur_smoke.untrusted_injection_true": grep_lines(cur_smoke, '"untrusted" in span_text or "injection" in span_text'),
        "cur_smoke.tool_markers": grep_lines(cur_smoke, 'if level == "tool" and has_word_or_phrase(span_text, UNTRUSTED_OBSERVATION_MARKERS)'),
        "cur_smoke.v3_def": grep_lines(cur_smoke, "def span_has_low_authority_injection_v3"),
        "cur_smoke.v3_reads": grep_lines(cur_smoke, 'text = str(span.get("text", "")).lower()'),
        "cur_smoke.has_conflict_def": grep_lines(cur_smoke, "def has_conflict"),
        "cur_smoke.conflict_triggers_read": grep_lines(cur_smoke, 'get("conflict_triggers"'),
        "snap_smoke.has_conflict_def": grep_lines(snap_smoke, "def has_conflict"),
        "snap_smoke.v3_def": grep_lines(snap_smoke, "def span_has_low_authority_injection_v3"),
        "snap_smoke.span_is_untrusted_observation_def": grep_lines(snap_smoke, "def span_is_untrusted_observation"),
        "cur_smoke.triggers_const": grep_lines(cur_smoke, "LOW_AUTHORITY_INJECTION_TRIGGERS = ("),
        "cur_smoke.labels_const": grep_lines(cur_smoke, "LOW_AUTHORITY_DECISION_LABELS = ("),
        "cur_smoke.ctx_v3_const": grep_lines(cur_smoke, "LOW_AUTHORITY_DECISION_CONTEXT_TERMS_V3 = ("),
        "cur_smoke.exfil_v3_const": grep_lines(cur_smoke, "LOW_AUTHORITY_SECRET_EXFIL_TERMS_V3 = ("),
        "cur_smoke.untrusted_markers_const": grep_lines(cur_smoke, "UNTRUSTED_OBSERVATION_MARKERS = ("),
        "ihc_runner.find_token_spans_call": grep_lines(C.REPO / "scripts/run_kvpress_ih_challenge.py", "token_spans = find_token_spans("),
        "ihc_runner.imports_from_legacy": grep_lines(C.REPO / "scripts/run_kvpress_ih_challenge.py", "from run_ih_challenge_kv import"),
        "o8k.authority_priority_sets_def": grep_lines(C.REPO / "scripts/run_outcome_informed_authority.py", "def authority_priority_sets"),
        "o8k.low_marker": grep_lines(C.REPO / "scripts/run_outcome_informed_authority.py", '"_low_" in str(span.get("span_id", ""))'),
        "o8k.high_marker": grep_lines(C.REPO / "scripts/run_outcome_informed_authority.py", '"_high_" in str(span.get("span_id", ""))'),
        "sysifeval.run_config.scan_chat": None,
    }
    S["loc"] = loc

    # ---------- (ii) detector-v3 constants and version diff ----------
    smoke_snap = load_module("smoke_snapshot_a0", snap_smoke)
    runner = C.load_runner("current")  # binds current smoke module as run_authoritykv_smoke
    smoke_cur = sys.modules["run_authoritykv_smoke"]
    consts = {
        "LOW_AUTHORITY_INJECTION_TRIGGERS": list(smoke_cur.LOW_AUTHORITY_INJECTION_TRIGGERS),
        "LOW_AUTHORITY_DECISION_LABELS": list(smoke_cur.LOW_AUTHORITY_DECISION_LABELS),
        "LOW_AUTHORITY_DECISION_CONTEXT_TERMS_V3": list(smoke_cur.LOW_AUTHORITY_DECISION_CONTEXT_TERMS_V3),
        "LOW_AUTHORITY_SECRET_EXFIL_TERMS_V3": list(smoke_cur.LOW_AUTHORITY_SECRET_EXFIL_TERMS_V3),
        "UNTRUSTED_OBSERVATION_MARKERS": list(smoke_cur.UNTRUSTED_OBSERVATION_MARKERS),
        "secret_substrings": ["akv_secret", "akv_trace_secret", "secret"],
    }
    same = {}
    for name in ("span_has_low_authority_injection_v3", "has_word_or_phrase", "span_token_set", "span_is_untrusted_observation", "detected_low_authority_token_set", "find_token_spans", "has_conflict"):
        same[name] = inspect.getsource(getattr(smoke_cur, name)) == inspect.getsource(getattr(smoke_snap, name))
    for name in ("LOW_AUTHORITY_INJECTION_TRIGGERS", "LOW_AUTHORITY_DECISION_LABELS", "LOW_AUTHORITY_DECISION_CONTEXT_TERMS_V3", "LOW_AUTHORITY_SECRET_EXFIL_TERMS_V3", "UNTRUSTED_OBSERVATION_MARKERS"):
        same["const:" + name] = tuple(getattr(smoke_cur, name)) == tuple(getattr(smoke_snap, name))
    S["detector"] = {"constants": consts, "counts": {k: len(v) for k, v in consts.items()}, "snapshot_vs_current_identical": same,
                     "v3_source": inspect.getsource(smoke_cur.span_has_low_authority_injection_v3)}

    # ---------- (iii) stored predictions: P/D provenance per setting ----------
    def agg(run: str, method: str, ratio: float, group_key=None):
        rows = [r for r in C.read_jsonl(RES / run / "predictions.jsonl") if r["method"] == method and abs(float(r["keep_ratio"]) - ratio) < 1e-9]
        groups = collections.defaultdict(list)
        for r in rows:
            g = group_key(r) if group_key else "all"
            groups[g].append(r)
        res = {}
        for g, rs in sorted(groups.items()):
            src = collections.Counter()
            for r in rs:
                for s in r.get("authority_token_spans", []):
                    src[f"{s.get('source')}/{s.get('level')}"] += 1
            P = [a["press_audit"][0]["protected_count"] for a in [r for r in rs if r.get("press_audit")] for _ in [0]]
            P = [r["press_audit"][0]["protected_count"] for r in rs if r.get("press_audit")]
            D = [r["press_audit"][0]["excluded_count"] for r in rs if r.get("press_audit")]
            res[g] = {"n": len(rs), "span_sources": dict(src), "P_min": min(P) if P else None, "P_med": sorted(P)[len(P) // 2] if P else None, "P_max": max(P) if P else None,
                      "D_min": min(D) if D else None, "D_med": sorted(D)[len(D) // 2] if D else None, "D_max": max(D) if D else None, "D_zero_count": sum(1 for d in D if d == 0), "n_audit": len(D)}
        return res
    rel = lambda r: r["category"]
    cond = lambda r: r["example_id"].rsplit("_", 1)[-1] if r["example_id"].endswith("clean") else ("explicit_attack" if r["example_id"].endswith("explicit_attack") else "paraphrase_attack")
    stored = {
        "IH full AKV (Qwen, Knorm 40%)": agg("aclmain_20260725v1_qwen7b_knorm_compositions500", "authority_knorm_detected_provenance", 0.4, rel),
        "IH R+P lexical gating (Qwen, Knorm 40%)": agg("aclmain_20260725v1_qwen7b_knorm_compositions500", "authority_knorm_provenance", 0.4, rel),
        "IH detector-only (Qwen, Knorm 40%)": agg("aclmain_20260725v1_qwen7b_knorm_compositions500", "authority_knorm_detected", 0.4, rel),
        "IH P-only (Qwen, Knorm 40%)": agg("aclmain_20260725v1_qwen7b_knorm_compositions500", "authority_knorm_pin", 0.4, rel),
        "IH system-only (Qwen, Knorm 40%)": agg("aclmain_20260725v1_qwen7b_knorm_compositions500", "system_knorm_pin", 0.4, rel),
        "IH all-control (Qwen, Knorm 40%)": agg("aclmain_20260725v1_qwen7b_knorm_compositions500", "all_control_knorm_pin", 0.4, rel),
        "mixed full AKV (Streaming 40%)": agg("arrmixed_20260726v4_qwen_streaming_full300", "authority_streaming_detected_provenance", 0.4, cond),
        "mixed detector-only (Streaming 40%)": agg("arrmixed_robustfull_20260727v2_qwen_streaming_detector40_300", "authority_streaming_detected", 0.4, cond),
        "mixed drop100 (Streaming 40%)": agg("arrmixed_robustfull_20260727v1_qwen_streaming_hybrid40_drop100_300", "authority_streaming_detected_provenance", 0.4, cond),
        "System-IFEval AKV (Knorm 40%)": agg("arrsys_20260726v4_qwen_knorm40_full150", "authority_knorm_detected_provenance", 0.4),
        "System-IFEval AKV (Streaming 40%)": agg("arrsys_20260726v4_qwen_streaming40_full150", "authority_streaming_detected_provenance", 0.4),
        "IH-Challenge AKV (Knorm 40%)": agg("aclfollow_20260725v2_qwen7b_ih_native_nonh2o40", "authority_knorm_detected_provenance", 0.4),
        "8k correct (SnapKV 2%)": agg("akvcausal_20260726v4_matched_long8k30", "authority_snapkv_v2_adaptive", 0.02, rel),
        "8k wrong (SnapKV 2%)": agg("akvcausal_20260726v4_matched_long8k30", "counterfactual_snapkv_v3_matched_wrong_authority", 0.02, rel),
    }
    S["stored"] = stored
    # IH-Challenge: the D span's text head and whether provenance/detector fire
    ihc = C.read_jsonl(C.REPO / "data/external_safety/ih_challenge_blue_team_auto_quoted_system_40.jsonl")
    S["ihc_span_examples"] = [{"id": r["id"], "span_id": r["metadata"]["authority_spans"][0]["span_id"], "start_marker": r["metadata"]["authority_spans"][0]["start_marker"]} for r in ihc[:2]]

    # ---------- (iv) counterfactual mutation (Q2 / R2 / R3) ----------
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-7B-Instruct", use_fast=True)

    def sets(smoke, example, include_chat=False, detector_scope="all"):
        context_text, context_ids, offsets, suffix_ids, _ = runner.prompt_parts(tok, example)
        if smoke is smoke_snap:
            spans = smoke.find_token_spans(context_text, offsets, example, span_source="metadata")
        else:
            spans = smoke.find_token_spans(context_text, offsets, example, span_source="metadata", include_low_authority_chat=include_chat)
        P = smoke.span_token_set(spans, {"system", "developer"})
        det_spans = spans if detector_scope == "all" else [s for s in spans if s.get("source") == "chat_message"]
        Ddet = smoke.detected_low_authority_token_set(det_spans, detector_version="v3")
        Dprov = smoke.untrusted_observation_token_set(spans)
        return frozenset(P), frozenset(Ddet), frozenset(Dprov), spans, len(context_ids)

    def mutate_fields(ex):
        m = json.loads(json.dumps(ex))
        for k in ("expected_behavior", "judge_rule", "low_authority_conflict", "high_authority_instruction", "authority_structure", "context", "category"):
            m.pop(k, None)
        md = m.get("metadata", {})
        for k in list(md.keys()):
            if k != "authority_spans":
                md.pop(k)
        return m

    def mutate_span_ids(ex):
        m = json.loads(json.dumps(ex))
        for k, s in enumerate(m.get("metadata", {}).get("authority_spans", [])):
            s["span_id"] = f"s{k}"
        return m

    def mutate_levels_shuffle_ids(ex):  # keep only level + markers (drop span_id entirely)
        m = json.loads(json.dumps(ex))
        for s in m.get("metadata", {}).get("authority_spans", []):
            s.pop("span_id", None)
        return m

    cf = {}
    for name, path, smoke, scope, chat in [
        ("IH-CacheBench main split (snapshot semantics)", "data/ih_cachebench/natural_short_500.jsonl", smoke_snap, "all", False),
        ("IH-Challenge 40 (snapshot semantics)", "data/external_safety/ih_challenge_blue_team_auto_quoted_system_40.jsonl", smoke_snap, "all", False),
        ("mixed-evidence 300 (current semantics, chat scan)", "data/mixed_evidence_attack/mixed_evidence_messages_all.jsonl", smoke_cur, "chat", True),
        ("System-IFEval 150 (current semantics, no chat scan)", "data/external_system_ifeval/sys_ifeval_messages_150.jsonl", smoke_cur, "chat", False),
        ("8k 30 (snapshot semantics)", "data/ih_cachebench/outcome_informed_long_8k_30.jsonl", smoke_snap, "all", False),
    ]:
        rows = C.read_jsonl(C.REPO / path)
        stat = {"n": len(rows), "M1_fields_removed_identical": 0, "M2_span_ids_opaque_identical": 0, "M3_span_id_dropped_identical": 0,
                "M2_changed_examples": [], "P_from_metadata_only_examples": 0, "P_sizes": [], "D_sizes": [], "multi_tier_P_includes_extra_developer": 0, "multi_tier_n": 0}
        for ex in rows:
            base = sets(smoke, ex, chat, scope)
            P, Ddet, Dprov, spans, n_ctx = base
            stat["P_sizes"].append(len(P)); stat["D_sizes"].append(len(Ddet | Dprov))
            m1 = sets(smoke, mutate_fields(ex), chat, scope)
            m2 = sets(smoke, mutate_span_ids(ex), chat, scope)
            m3 = sets(smoke, mutate_levels_shuffle_ids(ex), chat, scope)
            stat["M1_fields_removed_identical"] += int(m1[:3] == base[:3])
            stat["M2_span_ids_opaque_identical"] += int(m2[:3] == base[:3])
            stat["M3_span_id_dropped_identical"] += int(m3[:3] == base[:3])
            if m2[:3] != base[:3] and len(stat["M2_changed_examples"]) < 5:
                stat["M2_changed_examples"].append({"id": ex["id"], "P": len(P), "P_m2": len(m2[0]), "Ddet": len(Ddet), "Ddet_m2": len(m2[1]), "Dprov": len(Dprov), "Dprov_m2": len(m2[2])})
            chat_P = {i for s in spans if s.get("source") == "chat_message" and s.get("level") in ("system", "developer") for i in s["token_indices"]}
            if P - chat_P:
                stat["P_from_metadata_only_examples"] += 1
            if ex.get("category") == "multi_tier":
                stat["multi_tier_n"] += 1
                extra_dev = {i for s in spans if "_extra_developer" in str(s.get("span_id", "")) for i in s["token_indices"]}
                stat["multi_tier_P_includes_extra_developer"] += int(bool(extra_dev) and extra_dev <= P)
        stat["P_med"] = sorted(stat["P_sizes"])[len(rows) // 2]; stat["D_med"] = sorted(stat["D_sizes"])[len(rows) // 2]
        stat.pop("P_sizes"); stat.pop("D_sizes")
        cf[name] = stat
    S["counterfactual"] = cf

    # ---------- (v) Q6 provenance dropout tier ----------
    mixed = C.read_jsonl(C.REPO / "data/mixed_evidence_attack/mixed_evidence_messages_all.jsonl")
    q6 = {"n": 0, "dropped_span_absent_from_P_and_D": 0, "dropped_tokens_in_P": 0, "dropped_tokens_in_D": 0, "D_after_drop_zero": 0, "by_condition_D_after_drop": collections.defaultdict(list)}
    for ex in mixed:
        context_text, context_ids, offsets, suffix_ids, _ = runner.prompt_parts(tok, ex)
        spans = smoke_cur.find_token_spans(context_text, offsets, ex, span_source="metadata", include_low_authority_chat=True)
        dropped_tokens = {i for s in spans if s.get("source") == "metadata_marker" for i in s["token_indices"]}
        pert = runner.perturb_metadata_spans(spans, example_id=str(ex["id"]), seed=20260726, drop_rate=1.0, boundary_shrink_tokens=0)
        P = smoke_cur.span_token_set(pert, {"system", "developer"})
        Ddet = smoke_cur.detected_low_authority_token_set([s for s in pert if s.get("source") == "chat_message"], detector_version="v3")
        Dprov = smoke_cur.untrusted_observation_token_set(pert)
        D = Ddet | Dprov
        q6["n"] += 1
        q6["dropped_span_absent_from_P_and_D"] += int(not (dropped_tokens & (P | D)))
        q6["dropped_tokens_in_P"] += len(dropped_tokens & P); q6["dropped_tokens_in_D"] += len(dropped_tokens & D)
        q6["D_after_drop_zero"] += int(len(D) == 0)
        q6["by_condition_D_after_drop"][ex["metadata"]["condition"]].append(len(D))
    q6["by_condition_D_after_drop"] = {k: {"n": len(v), "zero": sum(1 for x in v if x == 0), "mean": round(sum(v) / len(v), 2), "max": max(v)} for k, v in q6["by_condition_D_after_drop"].items()}
    S["q6"] = q6

    # ---------- write ----------
    S["end_time"] = C.now_iso()
    C.write_json(out / "summary.json", S)
    C.write_json(out / "peak_mem.json", {"note": "CPU only"})
    (out / "log.txt").write_text("see summary.json\n")
    C.write_jsonl(out / "predictions.jsonl", [])
    cfg["end_time"] = C.now_iso(); C.write_json(out / "config.json", cfg)
    print(json.dumps({"run_dir": str(out), "callers": callers, "same": same, "cf": cf, "q6": q6}, indent=1, default=str)[:6000])


if __name__ == "__main__":
    main()
