# IH-Challenge Official KVPress Summary

Data-quality status: **PASS**.

Accuracy uses the preserved official grader. End-to-end accuracy includes infeasible and error outcomes; conditional accuracy includes only successfully executed, gradable pairs.

| Model | Method | KV keep | Eligible | End-to-end acc. | Conditional acc. | Injection follow | Infeasible | Errors |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 01-ai/Yi-1.5-9B-Chat | `fullkv` | 100% | 40/40 | 1/40 | 1/40 | 0/40 | 0 | 0 |
| 01-ai/Yi-1.5-9B-Chat | `fullkv` | 100% | 40/40 | 0/40 | 0/40 | 0/40 | 0 | 0 |

## Paired comparisons

| Model | Base | Comparison | KV keep | Base acc. | Comparison acc. | Delta | Exact p | Holm p |
|---|---|---|---:|---:|---:|---:|---:|---:|
