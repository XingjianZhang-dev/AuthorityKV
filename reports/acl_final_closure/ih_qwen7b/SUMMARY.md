# IH-Challenge Official KVPress Summary

Data-quality status: **PASS**.

Accuracy uses the preserved official grader. End-to-end accuracy includes infeasible and error outcomes; conditional accuracy includes only successfully executed, gradable pairs.

| Model | Method | KV keep | Eligible | End-to-end acc. | Conditional acc. | Injection follow | Infeasible | Errors |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen/Qwen2.5-7B-Instruct | `fullkv` | 100% | 40/40 | 35/40 | 35/40 | 5/40 | 0 | 0 |
| Qwen/Qwen2.5-7B-Instruct | `authority_h2o_detected_provenance` | 20% | 40/40 | 39/40 | 39/40 | 1/40 | 0 | 0 |
| Qwen/Qwen2.5-7B-Instruct | `authority_h2o_detected_provenance` | 40% | 40/40 | 40/40 | 40/40 | 0/40 | 0 | 0 |
| Qwen/Qwen2.5-7B-Instruct | `authority_knorm_detected_provenance` | 20% | 40/40 | 35/40 | 35/40 | 4/40 | 0 | 0 |
| Qwen/Qwen2.5-7B-Instruct | `authority_knorm_detected_provenance` | 40% | 40/40 | 40/40 | 40/40 | 0/40 | 0 | 0 |
| Qwen/Qwen2.5-7B-Instruct | `authority_snapkv_detected_provenance` | 20% | 40/40 | 40/40 | 40/40 | 0/40 | 0 | 0 |
| Qwen/Qwen2.5-7B-Instruct | `authority_snapkv_detected_provenance` | 40% | 40/40 | 40/40 | 40/40 | 0/40 | 0 | 0 |
| Qwen/Qwen2.5-7B-Instruct | `authority_streaming_detected_provenance` | 20% | 40/40 | 20/40 | 20/40 | 0/40 | 0 | 0 |
| Qwen/Qwen2.5-7B-Instruct | `authority_streaming_detected_provenance` | 40% | 40/40 | 32/40 | 32/40 | 1/40 | 0 | 0 |
| Qwen/Qwen2.5-7B-Instruct | `fullkv` | 100% | 40/40 | 37/40 | 37/40 | 3/40 | 0 | 0 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | 20% | 40/40 | 12/40 | 12/40 | 23/40 | 0 | 0 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | 40% | 40/40 | 30/40 | 30/40 | 10/40 | 0 | 0 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | 20% | 40/40 | 29/40 | 29/40 | 11/40 | 0 | 0 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | 40% | 40/40 | 30/40 | 30/40 | 10/40 | 0 | 0 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_pyramid` | 20% | 40/40 | 36/40 | 36/40 | 4/40 | 0 | 0 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_pyramid` | 40% | 40/40 | 36/40 | 36/40 | 4/40 | 0 | 0 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | 20% | 40/40 | 36/40 | 36/40 | 4/40 | 0 | 0 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | 40% | 40/40 | 36/40 | 36/40 | 4/40 | 0 | 0 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | 20% | 40/40 | 0/40 | 0/40 | 0/40 | 0 | 0 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | 40% | 40/40 | 0/40 | 0/40 | 0/40 | 0 | 0 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_tova` | 20% | 40/40 | 36/40 | 36/40 | 4/40 | 0 | 0 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_tova` | 40% | 40/40 | 36/40 | 36/40 | 4/40 | 0 | 0 |

## Paired comparisons

| Model | Base | Comparison | KV keep | Base acc. | Comparison acc. | Delta | Exact p | Holm p |
|---|---|---|---:|---:|---:|---:|---:|---:|
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | 12/37 | 36/37 | +64.9% | 1.19e-07 | 8.34e-07 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | 30/37 | 37/37 | +18.9% | 0.0156 | 0.0781 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | 29/37 | 35/37 | +16.2% | 0.0312 | 0.0938 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | 30/37 | 37/37 | +18.9% | 0.0156 | 0.0781 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `authority_snapkv_detected_provenance` | 20% | 36/37 | 37/37 | +2.7% | 1 | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `authority_snapkv_detected_provenance` | 40% | 36/37 | 37/37 | +2.7% | 1 | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | 0/37 | 20/37 | +54.1% | 1.91e-06 | 1.14e-05 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | 0/37 | 32/37 | +86.5% | 4.66e-10 | 3.73e-09 |
