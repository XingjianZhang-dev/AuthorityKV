# Extended experiments

These scripts extend the main harness (`scripts/`, `authoritykv_experiments/`) without changing it: the runner and
the press of the main experiments are imported, and their SHA-256 is checked at import time
(`akv_common.py`). Two revisions of the main runner are used. IH-CacheBench runs load the revision stored in
`repro_snapshots/acl_parent_20260725/`; System-IFEval and LongBench runs load the one in `scripts/`.

## Files

| File | Purpose |
|---|---|
| `akv_presses.py`, `akv_presses_t1.py`, `akv_presses_d2.py`, `d1_streaming_tiebreak.py` | Tie-breaking rules (recency, earliest position, seeded random), fixed per-layer budgets, soft-penalty and quota rules |
| `akv_variants.py` | How the protected and demoted tiers are built for each configuration (`rp`, `rpstrict`, `e3bdet`, classifier variants, `full`, pin-only baselines) |
| `akv_run_v5.py` | The generation runner. `akv_run.py` to `akv_run_v4.py` are its earlier revisions; each adds options and leaves the earlier ones unchanged, and the `config.json` of a run names the revision that produced it |
| `akv_select.py` | Selection-only analyses (prefill without generation): retained sets, retention by span type, offset constants |
| `x6_run.py`, `x8_run.py`, `x_ihc_run.py` | Wrappers for the Qwen2.5-14B capability checks and the IH-Challenge runs |
| `score_run.py`, `analyze_ih.py`, `analyze_mixed.py` | Scoring and paired analysis of finished runs |
| `verify_facts.py`, `robustness.py`, `facts.py` | Recompute every line of `results/RESPONSE_FACTS.jsonl` from the raw outputs |
| `t1_recount.py`, `t1_eq_check.py`, `t1_eq_ids.py`, `t1_unit.py` | Recount of the headline table under both tie-breaking rules, and checks of the tie-breaking functions |
| `build_run_index.py`, `build_x2_mistral.py` | Write `results/RUN_INDEX.csv` and `results/_derived/X2_mixed_mistral.json` |
| `a0_signal_sources.py`, `d1_sanity.py`, `d2_sanity.py`, `pg2_probe.py`, `overlay_check.py` | Audits: which fields the selector reads, tie-rule sanity checks, the Prompt Guard 2 label probe, and a re-run of the stored graders |
| `ids_mixed_*.txt` | Example-id lists used by `--ids-file` |

## Experiments

The `experiment` column of `results/RUN_INDEX.csv` uses these names.

| Name | Content |
|---|---|
| T1 | The main matrix under both tie-breaking rules: base, roles + provenance, span boundaries, and pin-only baselines on IH-CacheBench (three models), System-IFEval, and LongBench with an injected instruction |
| T1EQ | An explicit earliest-position rule reproduces the stored R↑ outputs on sampled examples |
| D1, D2 | Recency and seeded random tie-breaking; D1SANITY and D2SANITY compare retained sets at prefill |
| E1 | Filter-then-compress: delete the untrusted source, or exactly the demoted spans, before prefill |
| E2, E2full, X7 | Soft score penalties and reserved budget shares, tuned on a 120-item split and evaluated on the full split and on the other two models |
| E3, E3b, X3 | Grades of metadata on the main split and on the held-out surfaces: roles + provenance, the sentence-level lexical detector, Prompt Guard 2, and the DeBERTa classifier |
| E4, X2 | Detectors in place of annotation on LongBench with an injected instruction (Qwen2.5-7B and Mistral-7B) |
| E5, X1b | System-IFEval with further compressors and on Qwen2.5-14B |
| E6, X1a, X1a-ext, X1c, X6 | Qwen2.5-14B: IH-CacheBench, IH-Challenge, and capability checks on LongBench, RULER, and AgentDojo |
| X4, X5 | Four-budget curve and the 8k-token set at 2% KV for the annotation-free configurations |
| X8 | IH-Challenge with role-only and classifier-derived tiers |
| A0, A3, A4, A1A2A5A6 | Signal-source audit, offset-constant check, retention by span type, and analyses of stored predictions |
| OVL-T6T8, PG2PROBE | Re-run of the stored graders; Prompt Guard 2 label-index probe |

Identifiers such as `PREREG-25` in docstrings and in `config.json` name the analysis plan entry that fixed the
variants, examples, and pass rule of a run before it was executed.

The `command` field of each `runs/<run>/config.json` is the command line of that run, relative to the repository
root. The scripts and input files it names are in this repository: the five revisions of the generation runner,
the id lists here and under `runs/_t1_ids/`, and the datasets under `data/`. The one exception is the run
`A1A2A5A6`, a report over stored predictions whose numbers `verify_facts.py` recomputes.

## Variants

`--variants` of `akv_run_v5.py` takes a comma-separated list. The ones used in the paper:

| Variant | Protected tier | Demoted tier |
|---|---|---|
| `base`, `fullkv` | none | none (the official compressor; the full cache) |
| `system_pin`, `pin`, `all_control_pin` | system prompt only; system and developer spans; every typed control span | none |
| `rpstrict` | system and developer spans | all tool and retrieved-document text |
| `e3bdet`, `e3bclfpg2`, `e3bclfdeberta` | as `rpstrict` | as `rpstrict`, plus sentences flagged by the lexical detector, Prompt Guard 2, or the DeBERTa classifier |
| `e4det`, `e4clfpg2`, `e4clfdeberta` | system message | flagged sentences of the retrieved document (LongBench task) |
| `full` | system and developer spans | lower-authority spans flagged by the lexical detector on marked spans |
| `e1a`, `e1b` | filter-then-compress: the whole untrusted source, or exactly the demoted spans, is deleted before prefill | |
| `softsigma:<a>`, `softconst:<c>`, `quota:<q>`, `quotad:<q>` | soft score penalties and reserved budget shares with the tiers of `full` | |

`--tie-break topk` is R↑ of the paper and `--tie-break recency` is R↓.
