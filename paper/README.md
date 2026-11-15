# Paper, tables, and figures

`AuthorityKV_EACL2027.pdf` is the paper. Every generated table and figure in it is built from records in this
repository by the tools in `tools/`; run them from the repository root.

```bash
python paper/tools/gen_tables.py results paper/generated     # from the fact files
python paper/tools/gen_tables_statistics.py                  # from the statistics of the main matrix
python paper/tools/gen_tables_standard_tasks.py              # from the stored grader outputs
python paper/tools/make_figs.py results paper/figures        # Figures 2 and 3
bash   paper/tools/recompute_statistics.sh                   # recompute the statistics from the raw predictions
```

The first four commands leave `git status` clean. The fifth re-runs the analysis on the raw predictions
(extract `raw_outputs/` first) and compares its output with the 46 stored statistics files.

## Tables

| Table | File in `generated/` | Tool | Records |
|---|---|---|---|
| 2 | `cr_ladder.tex` | `gen_tables.py` | `results/T1_facts.json`; `results/RESPONSE_FACTS.jsonl` (experiments E3, E3b) |
| 3 | `cr_external.tex` | `gen_tables.py` | `results/T1_facts.json`; `results/RESPONSE_FACTS.jsonl` (experiments X1b) |
| 4 | `cr_alternatives.tex` | `gen_tables.py` | `results/T1_facts.json`; `results/RESPONSE_FACTS.jsonl` (experiments E1, E2, E2full) |
| 6 | `cr_app_ih_cells.tex` | `gen_tables.py` | `results/T1_facts.json` |
| 7 | `cr_app_detectors.tex` | `gen_tables.py` | `results/RESPONSE_FACTS.jsonl` (experiments E3, E3b) |
| 8 | `cr_app_14b.tex` | `gen_tables.py` | `results/RESPONSE_FACTS.jsonl` (experiments E6) |
| 9 | `cr_app_heldout.tex` | `gen_tables.py` | `results/RESPONSE_FACTS.jsonl` (experiments X3) |
| 10 | `cr_app_sysifeval.tex` | `gen_tables.py` | `results/RESPONSE_FACTS.jsonl` (experiments A1A2A5A6, E5); the stored summaries of those two runs under `runs/` (all-150 counts) |
| 11 | `cr_app_mixed.tex` | `gen_tables.py` | `results/T1_facts.json` |
| 12 | `cr_app_retention.tex` | `gen_tables.py` | `results/RESPONSE_FACTS.jsonl` (experiments A1A2A5A6, A4) |
| 13 | `cr_app_classifier.tex` | `gen_tables.py` | `results/RESPONSE_FACTS.jsonl` (experiments E4) |
| 14 | `cr_app_mistral_mixed.tex` | `gen_tables.py` | `results/RESPONSE_FACTS.jsonl` (experiments X2); `results/_derived/X2_mixed_mistral.json` |
| 15 | `cr_app_filter.tex` | `gen_tables.py` | `results/RESPONSE_FACTS.jsonl` (experiments E1) |
| 16 | `cr_app_softquota.tex` | `gen_tables.py` | `results/RESPONSE_FACTS.jsonl` (experiments E2, E2full); the stored summary of the full-split StreamingLLM run under `runs/` |
| 17 | `cr_app_dropout.tex` | `gen_tables.py` | `results/T1_facts.json` |
| 20 | `appendix_ifeval_table.tex` | `gen_tables_standard_tasks.py` | `reports/arr_august_external_closure/full/system_ifeval_full_v4_metrics.json` |
| 21 | `appendix_mixed_table.tex` | `gen_tables_standard_tasks.py` | `reports/arr_august_external_closure/full/mixed_evidence_*_full_v4_metrics.json` |
| 22 | `appendix_mixed_conditions_table.tex` | `gen_tables_standard_tasks.py` | `reports/arr_august_external_closure/full/mixed_evidence_*_full_v4_metrics.json` |
| 33 | `appendix_crossmodel_table.tex` | `gen_tables_statistics.py` | `reports/acl_final_closure/parent_statistics/method_summary.csv` |
| 34 | `appendix_category_table.tex` | `gen_tables_statistics.py` | `reports/acl_final_closure/parent_statistics/category_summary.csv` |
| 35 | `appendix_position_table.tex` | `gen_tables_statistics.py` | `reports/acl_final_closure/parent_statistics/position_summary.csv` |
| 36 | `appendix_primary_paired_table.tex` | `gen_tables_statistics.py` | `reports/acl_final_closure/parent_statistics/paired_comparisons.csv` |
| 39 | `appendix_crossmodel_ablation_table.tex` | `gen_tables_statistics.py` | `reports/acl_final_closure/parent_statistics/method_summary.csv` |
| 41 | `appendix_matched_table.tex` | `gen_tables_statistics.py` | `reports/akvcausal_20260726v4_matched/paired_comparisons.csv` |
| 42 (rows) | `cr_app_curve_rows.tex` | `gen_tables.py` | `results/RESPONSE_FACTS.jsonl` (experiments X4) |
| 43 | `cr_app_ihc.tex` | `gen_tables.py` | `results/RESPONSE_FACTS.jsonl` (experiments X8); `reports/acl_final_closure/ih_qwen7b/method_summary.csv` |
| 44 | `appendix_utility_table.tex` | `gen_tables_statistics.py` | `reports/acl_final_closure/parent_utility/utility_summary.csv` |
| 45 | `appendix_systems_table.tex` | `gen_tables_statistics.py` | `reports/aclfollow_20260725v2_randomized_systems/*.csv` |
| 46 (rows) | `appendix_crossmodel_external_gate_rows.tex` | `gen_tables_standard_tasks.py` | `reports/arr_august_external_closure/upgrade/crossmodel_gate_decision.json` |
| 46 (rows) | `cr_app_gate_rows.tex` | `gen_tables.py` | `results/RESPONSE_FACTS.jsonl` (experiments X1c, X6) |
| 47 | `appendix_endpoint_guardrails_table.tex` | `gen_tables_statistics.py` | `reports/acl_final_closure/parent_statistics/method_summary.csv` |

Experiment names refer to the `experiment` column of `results/RUN_INDEX.csv`; `review_experiments/README.md`
describes them. Each line of `results/RESPONSE_FACTS.jsonl` names the run and the field it is computed from, and
`review_experiments/verify_facts.py` recomputes all of them from the raw outputs.

Table 5 summarizes the matched 8k intervention of Table 41, and Table 38 reports the position-balanced
replication from `reports/acl_final_closure/no_prefix_statistics/`. The remaining tables define terms, describe
the protocol, or give worked examples and are written in the paper.

## Figures

| Figure | File in `figures/` | Source |
|---|---|---|
| 1 | `fig1_overview.pdf` | `fig1_overview.tex` (TikZ; `pdflatex fig1_overview_standalone.tex` in `figures/`) |
| 2 | `fig2_results.pdf` | `tools/make_figs.py` from `results/T1_facts.json` |
| 3 | `fig3_retention.pdf` | `tools/make_figs.py` from `results/RESPONSE_FACTS.jsonl` (experiment A4) |

`generated/cr_numbers.json` and `generated/cr_fact_ids_used.json` list the headline numbers and the fact ids
that the tables read.
