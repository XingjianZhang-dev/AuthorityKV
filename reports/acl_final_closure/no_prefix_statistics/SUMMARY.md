# ACL Main Official Sweep Summary

Data-quality status: **PASS**.

Complete run directories: 3/3.

## Method-level results

| Model | Method | KV keep | Feasible | ARR | Hierarchy success | Benign utility | Errors | Median prefill (s) | Median peak MB |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen/Qwen2.5-7B-Instruct | `authority_h2o_detected_provenance` | 20% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 0.4172 | 28209.2 |
| Qwen/Qwen2.5-7B-Instruct | `authority_h2o_detected_provenance` | 40% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 0.4104 | 28250.5 |
| Qwen/Qwen2.5-7B-Instruct | `authority_knorm_detected_provenance` | 20% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 0.2071 | 14952.3 |
| Qwen/Qwen2.5-7B-Instruct | `authority_knorm_detected_provenance` | 40% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 0.2044 | 14995.1 |
| Qwen/Qwen2.5-7B-Instruct | `authority_streaming_detected_provenance` | 20% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 0.2072 | 14952.3 |
| Qwen/Qwen2.5-7B-Instruct | `authority_streaming_detected_provenance` | 40% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 0.2043 | 14995.1 |
| Qwen/Qwen2.5-7B-Instruct | `fullkv` | 100% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 0.1914 | 15076.7 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | 20% | 120/120 | 32/100 | 46/100 | 18/20 | 0 | 0.4089 | 28209.2 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | 40% | 120/120 | 35/100 | 65/100 | 1/20 | 0 | 0.4027 | 28250.5 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | 20% | 120/120 | 13/100 | 79/100 | 18/20 | 0 | 0.1974 | 14952.3 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | 40% | 120/120 | 6/100 | 94/100 | 20/20 | 0 | 0.1949 | 14995.1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | 20% | 120/120 | 50/100 | 0/100 | 2/20 | 0 | 0.1976 | 14952.3 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | 40% | 120/120 | 90/100 | 10/100 | 2/20 | 0 | 0.1949 | 14995.1 |

## Paired comparisons

| Model | Base | Comparison | KV keep | Base ARR | Comparison ARR | Relative reduction | Exact p | Holm p |
|---|---|---|---:|---:|---:|---:|---:|---:|
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | 32/100 | 0/100 | 100.0% | 4.66e-10 | 1.4e-09 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | 35/100 | 0/100 | 100.0% | 5.82e-11 | 2.33e-10 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | 13/100 | 0/100 | 100.0% | 0.000244 | 0.000488 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | 6/100 | 0/100 | 100.0% | 0.0312 | 0.0312 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | 50/100 | 0/100 | 100.0% | 1.78e-15 | 8.88e-15 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | 90/100 | 0/100 | 100.0% | 1.62e-27 | 9.69e-27 |

## Paired secondary endpoints

These endpoints use a separate global Holm family; the registered authority-reversal family above is unchanged.

| Model | Base | Comparison | KV keep | Endpoint | Scope | Base | Comparison | Delta | Holm p |
|---|---|---|---:|---|---|---:|---:|---:|---:|
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | hierarchy_success | conflict | 46/100 | 100/100 | +54.0% | 1.33e-15 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | benign_utility | benign | 18/20 | 20/20 | +10.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | strict_json | all_fullkv_correct | 118/120 | 42/120 | -63.3% | 3.44e-22 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | hierarchy_success | conflict | 65/100 | 100/100 | +35.0% | 6.4e-10 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | benign_utility | benign | 1/20 | 20/20 | +95.0% | 3.05e-05 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | strict_json | all_fullkv_correct | 120/120 | 38/120 | -68.3% | 5.79e-24 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | hierarchy_success | conflict | 79/100 | 100/100 | +21.0% | 8.58e-06 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | benign_utility | benign | 18/20 | 20/20 | +10.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | strict_json | all_fullkv_correct | 112/120 | 22/120 | -75.0% | 2.58e-26 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | hierarchy_success | conflict | 94/100 | 100/100 | +6.0% | 0.156 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | benign_utility | benign | 20/20 | 20/20 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | strict_json | all_fullkv_correct | 120/120 | 28/120 | -76.7% | 6.87e-27 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | hierarchy_success | conflict | 0/100 | 100/100 | +100.0% | 2.84e-29 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | benign_utility | benign | 2/20 | 20/20 | +90.0% | 5.34e-05 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | strict_json | all_fullkv_correct | 51/120 | 101/120 | +41.7% | 3.91e-09 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | hierarchy_success | conflict | 10/100 | 100/100 | +90.0% | 2.58e-26 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | benign_utility | benign | 2/20 | 20/20 | +90.0% | 5.34e-05 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | strict_json | all_fullkv_correct | 101/120 | 105/120 | +3.3% | 1 |

## Pooled descriptive comparisons

Pooled intervals resample prompt IDs as clusters, keeping cross-model replicas together; exact tests above remain model/dataset stratified.

| Base | Comparison | KV keep | Base ARR | Comparison ARR | Relative reduction | Cluster-bootstrap delta 95% CI |
|---|---|---:|---:|---:|---:|---:|
| `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | 32/100 | 0/100 | 100.0% | [-0.410, -0.230] |
| `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | 35/100 | 0/100 | 100.0% | [-0.440, -0.260] |
| `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | 13/100 | 0/100 | 100.0% | [-0.200, -0.070] |
| `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | 6/100 | 0/100 | 100.0% | [-0.110, -0.020] |
| `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | 50/100 | 0/100 | 100.0% | [-0.600, -0.400] |
| `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | 90/100 | 0/100 | 100.0% | [-0.950, -0.840] |
