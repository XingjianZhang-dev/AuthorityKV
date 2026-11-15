# Official External Utility Summary

Data-quality status: **PASS**.

Exact official-base/Authority no-span equivalence: 600/600 paired outputs.
FullKV/Authority paired utility comparisons: 12.

| Dataset | Method | KV keep | Accuracy | LongBench score | Median prefill (s) | Median peak MB |
|---|---|---:|---:|---:|---:|---:|
| longbench_official_2wikimqa_50.jsonl | `authority_h2o_detected_provenance` | 20% | 16/50 | 0.328 | 1.3558 | 24594.5 |
| longbench_official_2wikimqa_50.jsonl | `authority_h2o_detected_provenance` | 40% | 19/50 | 0.372 | 1.3567 | 24655.3 |
| longbench_official_2wikimqa_50.jsonl | `authority_knorm_detected_provenance` | 20% | 7/50 | 0.120 | 0.7866 | 15427.9 |
| longbench_official_2wikimqa_50.jsonl | `authority_knorm_detected_provenance` | 40% | 13/50 | 0.255 | 0.7580 | 15491.8 |
| longbench_official_2wikimqa_50.jsonl | `authority_streaming_detected_provenance` | 20% | 16/50 | 0.320 | 0.7661 | 15427.9 |
| longbench_official_2wikimqa_50.jsonl | `authority_streaming_detected_provenance` | 40% | 19/50 | 0.334 | 0.7869 | 15491.8 |
| longbench_official_2wikimqa_50.jsonl | `fullkv` | 100% | 19/50 | 0.402 | 0.7640 | 15689.3 |
| longbench_official_2wikimqa_50.jsonl | `kvpress_h2o` | 20% | 16/50 | 0.328 | 1.3533 | 24594.5 |
| longbench_official_2wikimqa_50.jsonl | `kvpress_h2o` | 40% | 19/50 | 0.372 | 1.3507 | 24655.3 |
| longbench_official_2wikimqa_50.jsonl | `kvpress_knorm` | 20% | 7/50 | 0.120 | 0.7501 | 15427.9 |
| longbench_official_2wikimqa_50.jsonl | `kvpress_knorm` | 40% | 13/50 | 0.255 | 0.7461 | 15491.8 |
| longbench_official_2wikimqa_50.jsonl | `kvpress_streaming` | 20% | 16/50 | 0.320 | 0.7747 | 15427.9 |
| longbench_official_2wikimqa_50.jsonl | `kvpress_streaming` | 40% | 19/50 | 0.334 | 0.7677 | 15491.8 |
| longbench_official_triviaqa_50.jsonl | `authority_h2o_detected_provenance` | 20% | 46/50 | 0.904 | 1.6514 | 25953.8 |
| longbench_official_triviaqa_50.jsonl | `authority_h2o_detected_provenance` | 40% | 45/50 | 0.890 | 1.6515 | 26019.2 |
| longbench_official_triviaqa_50.jsonl | `authority_knorm_detected_provenance` | 20% | 27/50 | 0.318 | 0.8253 | 15483.7 |
| longbench_official_triviaqa_50.jsonl | `authority_knorm_detected_provenance` | 40% | 37/50 | 0.556 | 0.8429 | 15552.8 |
| longbench_official_triviaqa_50.jsonl | `authority_streaming_detected_provenance` | 20% | 47/50 | 0.543 | 0.8378 | 15483.7 |
| longbench_official_triviaqa_50.jsonl | `authority_streaming_detected_provenance` | 40% | 48/50 | 0.647 | 0.8393 | 15552.8 |
| longbench_official_triviaqa_50.jsonl | `fullkv` | 100% | 48/50 | 0.958 | 0.8525 | 15762.6 |
| longbench_official_triviaqa_50.jsonl | `kvpress_h2o` | 20% | 46/50 | 0.904 | 1.6418 | 25953.8 |
| longbench_official_triviaqa_50.jsonl | `kvpress_h2o` | 40% | 45/50 | 0.890 | 1.6470 | 26019.2 |
| longbench_official_triviaqa_50.jsonl | `kvpress_knorm` | 20% | 27/50 | 0.318 | 0.8209 | 15483.7 |
| longbench_official_triviaqa_50.jsonl | `kvpress_knorm` | 40% | 37/50 | 0.556 | 0.8527 | 15552.8 |
| longbench_official_triviaqa_50.jsonl | `kvpress_streaming` | 20% | 47/50 | 0.543 | 0.8537 | 15483.7 |
| longbench_official_triviaqa_50.jsonl | `kvpress_streaming` | 40% | 48/50 | 0.647 | 0.8630 | 15552.8 |
| ruler_official_qwen25_4k_24.jsonl | `fullkv` | 100% | 12/24 | n/a | 0.5168 | 15309.6 |
