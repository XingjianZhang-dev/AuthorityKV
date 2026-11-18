# Runs of the extended experiments

One directory per run of the extended experiments: both
tie-breaking rules, the roles + provenance and detector configurations,
filter-then-compress, soft-penalty and quota baselines, Qwen2.5-14B, and the
selection audits. Directory names follow
`<UTC date>-<time>_<experiment>_<model>_<scorer>_<budget>[-<tie rule>]`.

| File | In git | Content |
|---|---|---|
| `config.json` | yes | Experiment id, model and tokenizer revisions, scorer, budgets, tie rule, variants, seeds, source hashes, environment |
| `run_config.json` | yes | Runner arguments in the format of the main experiments |
| `summary.json` | yes | Per-cell counts and audits computed when the run finished |
| `metrics.json`, `scored_metrics.json`, `scored_inputs.json` | yes | Task metrics (System-IFEval and LongBench runs) |
| `peak_mem.json` | yes | Peak GPU memory |
| `predictions.jsonl` | archive | One record per example, method, and budget: output text, generated token ids, retained-token audit |
| `judged_predictions.jsonl` | archive | The same records with the deterministic IH-CacheBench judgment |
| `scored_judgments.jsonl` | archive | Per-prompt System-IFEval judgments from the official grader |

The files marked *archive* are in
`authoritykv_review_experiments_runs.tar.zst`. Extract it at the repository
root:

```bash
zstd -dc authoritykv_review_experiments_runs.tar.zst | tar -xf -
```

`results/RUN_INDEX.csv` lists every run with its model, task, scorers,
budgets, and tie rule. Each line of `results/RESPONSE_FACTS.jsonl` names the
run and the field it is computed from, and
`python review_experiments/verify_facts.py` recomputes all of them from
these directories.

The source hashes in `config.json` identify the files used at run time. The
modules in `review_experiments/` are those files; they differ from the
hashed versions only in docstrings and in the name of their directory. Paths
that begin with `/workspace/authoritykv/` refer to the repository root.
