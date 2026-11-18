# Runner snapshot of the primary experiment matrix

This directory holds the method, runner, judge, and launcher files exactly as they were when the primary
IH-CacheBench matrix was run. Their SHA-256 values are the ones stored in the `source_hashes` of those runs, and
`review_experiments/akv_common.py` checks them before loading the runner for the extended IH-CacheBench experiments.

The files under `scripts/` and `authoritykv_experiments/` are the later revision. It adds the controls for
missing or imprecise provenance, the priority policy for system prompts longer than the budget, and the handling
of non-finite scores, and it is the revision used by the System-IFEval and LongBench runs. Every run records
which revision it used, so each recorded command line can be executed against the code that produced it.
