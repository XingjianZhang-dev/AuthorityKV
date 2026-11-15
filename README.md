# AuthorityKV: Preventing Authority Reversals in KV-Cache Compression

Code, benchmark, and results for the EACL 2027 paper by Xingjian Zhang (Carnegie Mellon University).

[Paper (PDF)](paper/AuthorityKV_EACL2027.pdf) · [Dataset on the Hugging Face Hub](https://huggingface.co/datasets/XingjianZhangDev/AuthorityKV) · [Where each table comes from](paper/README.md)

![One prompt, one budget, three caches](assets/overview.png)

KV-cache compression keeps the prompt tokens a scorer finds most recent or most salient and evicts the rest.
A prompt, however, mixes sources with different authority: system and developer instructions must override
conflicting text from users, tools, and retrieved documents. When compression evicts the governing instruction
and keeps the conflicting one, a model that was right with its full cache follows the lower-authority source.
We call this a *compression-induced authority reversal*.

**AuthorityKV** is a training-free rule that plugs into any score-based compressor at an unchanged budget. It
sorts tokens into three tiers (protected, eligible, demoted) and ranks by tier first and by the original score
second.

## Results

Authority reversals on IH-CacheBench, summed over three models (Qwen2.5-7B, Mistral-7B, Yi-1.5-9B), three
compressors (H2O, Knorm, StreamingLLM), and two budgets (20% and 40% of the prompt cache):

| Configuration | What marks the demoted tier | Reversals (of 7,200) | Benign controls solved (of 1,800) |
|---|---|---:|---:|
| Official compressors | n/a | 2,055 | 1,086 |
| + AuthorityKV, roles + provenance | source type only | 176 | 1,800 |
| + sentence-level detector | detector on raw text, no annotation | 52 | 1,800 |
| + span boundaries | detector on marked spans | 0 | 1,800 |

On System-IFEval (Qwen2.5-7B, StreamingLLM at 40%), the number of system prompts still satisfied after
compression rises from 8 to 48 of 88 (62 under a recency tie-breaking rule). On LongBench questions whose
source document also contains an injected instruction, successful attacks fall from 7 and 6 of 64 to 0 while
the answer stays in the cache. Every number in the paper is generated from records in this repository.

## Quickstart

```bash
python3.12 -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements-cpu.txt      # torch, transformers, and a pinned revision of NVIDIA KVPress
python examples/quickstart.py                      # Qwen2.5-0.5B-Instruct; a laptop CPU is enough
```

The example compresses a prompt that contains a system rule and a tool note contradicting it, and prints what
each cache keeps:

```
cache                               system rule kept  tool note kept
kvpress_streaming                                 3%            100%
kvpress_streaming + AuthorityKV                 100%              0%

Both caches keep 674 tokens in every layer.
```

In your own code, wrap any score-based KVPress compressor:

```python
from authoritykv_experiments.kvpress_authority import AuthorityAwarePress, build_official_press

base = build_official_press("kvpress_knorm", compression_ratio=0.6)   # keep 40% of the prompt cache

press = AuthorityAwarePress(
    base_press=base,
    compression_ratio=0.6,
    protected_token_indices=protected_ids,   # tier P: system and developer spans
    excluded_token_indices=demoted_ids,      # tier D: lower-authority text marked as conflicting
    strict_protected_budget=True,            # False keeps the best-scored part of P when P exceeds the budget
)

with press(model):                           # KVPress forward hooks prune the prefill cache
    model(**prompt_inputs)
```

`build_official_press` accepts `kvpress_snapkv`, `kvpress_h2o`, `kvpress_streaming`, `kvpress_tova`,
`kvpress_knorm`, and `kvpress_pyramid`. The token indices come from the orchestrator's role and provenance
metadata; `examples/quickstart.py` derives them from character spans, and `scripts/run_kvpress_authority.py`
from typed chat messages and span annotations. The whole method is `authoritykv_experiments/kvpress_authority.py`
(250 lines). The recency tie-breaking rule of the paper (R↓) is `review_experiments/akv_presses.py`.

## IH-CacheBench

400 conflicts and 100 conflict-free controls over five authority relations (system vs. user, developer vs.
user, system vs. tool, developer vs. retrieved document, multi-tier), each with an exact, automatically
checked answer, plus three held-out surfaces, a position-balanced replication split, and an 8k-token matched
set. `DATASET_CARD.md` documents construction, schema, and judging.

```python
from datasets import load_dataset

bench = load_dataset("XingjianZhangDev/AuthorityKV", "ih_cachebench", split="main")
```

The same files are under `data/ih_cachebench/`. They are generated from fixed seeds:
`bash scripts/build_ih_cachebench.sh` rebuilds all seven and checks that each is byte-identical to the released file.

## Reproducing the paper

Steps 1 and 2 need no GPU.

### 1. Recompute the reported numbers from the raw outputs

Every run stores one record per example, method, and budget: the output text, the generated token ids, the
retained-token audit, and the deterministic judgment. These records (5.0 GB uncompressed) ship as two archives
in `raw_outputs/` and are mirrored on the Hugging Face Hub. Extract them at the repository root:

```bash
zstd -dc raw_outputs/authoritykv_main_experiments_predictions.tar.zst | tar -xf -   # results/authoritykv/*/
zstd -dc raw_outputs/authoritykv_review_experiments_runs.tar.zst      | tar -xf -   # runs/*/
```

Then:

```bash
python review_experiments/verify_facts.py      # recomputes all 3,403 lines of results/RESPONSE_FACTS.jsonl (about 10 min)
python review_experiments/t1_recount.py        # the headline table under both tie-breaking rules
bash paper/tools/recompute_statistics.sh       # the statistics files behind the appendix tables (about 10 min)
```

The last command re-runs the paired tests, bootstrap intervals, and official graders on the raw predictions and
reports whether each of the 46 statistics files under `reports/` is reproduced byte for byte. The System-IFEval
step needs the grader environment: `python -m pip install -r requirements-eval.txt` and
`python -m nltk.downloader punkt_tab`.

### 2. Regenerate the tables and figures

```bash
python paper/tools/gen_tables.py results paper/generated     # Tables 2-4, 6-17 and 43 from the fact files
python paper/tools/gen_tables_statistics.py                  # appendix tables of the main matrix
python paper/tools/gen_tables_standard_tasks.py              # appendix tables of the standard tasks
python paper/tools/make_figs.py results paper/figures        # Figures 2 and 3
```

`git status` stays clean afterwards. `paper/README.md` maps every table and figure of the paper to its file,
its command, and the records it is built from.

### 3. Re-run experiments

Each run uses a single A100-80GB GPU and the environment of `requirements-gpu.txt`. The command line, model revision, and source hashes of every reported
run are stored with it: `results/authoritykv/<run>/run_config.json` for the main experiments and
`runs/<run>/config.json` for the experiments added during peer review; `results/RUN_INDEX.csv` lists all 261
runs. For example, the main matrix on one model and scorer:

```bash
python scripts/run_kvpress_authority.py \
  --run-id demo_qwen7b_knorm \
  --model Qwen/Qwen2.5-7B-Instruct \
  --dataset data/ih_cachebench/natural_short_500.jsonl \
  --methods fullkv,kvpress_knorm,authority_knorm_provenance,authority_knorm_detected_provenance \
  --keep-ratios 0.2,0.4 --max-new-tokens 16 --dtype bf16 \
  --assistant-prefix '{"decision":"' --stop-after-json-object \
  --out-dir results/authoritykv/demo_qwen7b_knorm
python scripts/judge_authoritykv.py --run-dir results/authoritykv/demo_qwen7b_knorm
```

and one cell of the tie-rule and metadata-grade experiments:

```bash
python review_experiments/akv_run_v5.py --experiment demo --prereg none --runner snapshot --task ih \
  --model Qwen/Qwen2.5-7B-Instruct --model-tag qwen7b --dataset data/ih_cachebench/natural_short_500.jsonl \
  --scorer streaming --keep-ratios 0.2,0.4 --variants base,rpstrict,full --tie-break recency \
  --out-dir runs/demo_streaming_recency
```

`review_experiments/README.md` lists the experiments and the variants each script accepts.

## Repository layout

```
authoritykv_experiments/   The method: AuthorityAwarePress and supporting cache-selection code
examples/                  quickstart.py
scripts/                   Benchmark construction, runners, graders, and statistics of the main experiments
review_experiments/        Tie-breaking rules, soft-penalty and quota baselines, filter-then-compress,
                           annotation-free detectors, and the verification code, added during peer review
repro_snapshots/           The runner revision used for the IH-CacheBench runs of review_experiments/
configs/                   Experiment matrices passed to the runners (their hashes are stored with each run)
data/                      IH-CacheBench and the derived evaluation sets (see DATASET_CARD.md)
results/                   Run records of the main experiments; RUN_INDEX.csv; RESPONSE_FACTS.jsonl and
                           T1_facts.json hold every number of the review-period experiments with its source run
runs/                      Run records of the review-period experiments
raw_outputs/               Per-example outputs and judgments of all 261 runs (two archives, 27 MB)
reports/                   Statistics computed from the raw outputs; inputs of the appendix tables
paper/                     The paper, its generated tables and figure sources, and the tools that build them
external/                  Pinned third-party evaluation code (System-IFEval grader)
tests/                     Unit tests
```

## Tests

```bash
python -m pytest -q tests                      # 91 tests, CPU only
python review_experiments/t1_unit.py           # the two tie-breaking rules against a reference implementation
```

## Citation

```bibtex
@inproceedings{zhang-2027-authoritykv,
  title     = {{AuthorityKV}: Preventing Authority Reversals in {KV}-Cache Compression},
  author    = {Zhang, Xingjian},
  booktitle = {Proceedings of the 20th Conference of the European Chapter of the Association for Computational Linguistics},
  year      = {2027},
  address   = {Athens, Greece},
  publisher = {Association for Computational Linguistics}
}
```

## License

Project-authored code and IH-CacheBench are released under Apache-2.0 (`LICENSE`). Third-party data and code
keep their original terms, listed in `THIRD_PARTY_NOTICES.md`. The method is training-free, so the release
contains no model weights.
