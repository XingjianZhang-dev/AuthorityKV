# Raw outputs

Per-example outputs of all 261 runs indexed in `results/RUN_INDEX.csv`.

| Archive | Restores | Runs | Uncompressed |
|---|---|---:|---:|
| `authoritykv_main_experiments_predictions.tar.zst` | `results/authoritykv/<run>/predictions.jsonl`, `judged_predictions.jsonl` | 69 | 1.1 GB |
| `authoritykv_review_experiments_runs.tar.zst` | `runs/<run>/predictions.jsonl`, `judged_predictions.jsonl`, `scored_judgments.jsonl` | 192 | 3.9 GB |

Extract both at the repository root:

```bash
zstd -dc raw_outputs/authoritykv_main_experiments_predictions.tar.zst | tar -xf -
zstd -dc raw_outputs/authoritykv_review_experiments_runs.tar.zst      | tar -xf -
```

Each archive also carries the configuration and metric files that are
already tracked in git, so it can be used on its own. `SHA256SUMS` lists the
archive checksums (`sha256sum -c SHA256SUMS` from this directory). The
extracted record files are ignored by git.

A record in `predictions.jsonl` holds the example id, method, and budget,
the output text, and the generated token ids. `judged_predictions.jsonl`
adds the deterministic IH-CacheBench judgment, and `scored_judgments.jsonl`
holds the per-prompt System-IFEval result from the official grader. The
record formats of the review-period runs are described in `runs/README.md`.
