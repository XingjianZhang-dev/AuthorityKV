# GPU compute inventory

Generated: 2026-07-27T19:02:29.792798+08:00

This is a conservative reconstruction from saved `run_config.json`
start/end timestamps. It counts process-GPU wall time for every
timestamp-complete run, including pilots, negative results, invalidated
runs, and reruns. It does not infer time for configs lacking timestamps.

## Headline

- Timestamp-complete GPU runs: 222
- Reconstructed process-GPU hours: 36.314
- Configs excluded for missing/invalid timestamps: 109
- Nonzero recorded runner exits among measured runs: 0

The total is suitable as a transparent lower bound for the Responsible
NLP checklist. Concurrent processes are counted separately because each
consumed GPU resources; elapsed node wall time would be smaller.

## By model

| Model | Runs | Process-GPU hours |
|---|---:|---:|
| `Qwen/Qwen2.5-7B-Instruct` | 185 | 26.916 |
| `01-ai/Yi-1.5-9B-Chat` | 10 | 5.324 |
| `mistralai/Mistral-7B-Instruct-v0.3` | 13 | 3.311 |
| `Qwen/Qwen2.5-14B-Instruct` | 9 | 0.757 |
| `microsoft/Phi-3.5-mini-instruct` | 1 | 0.004 |
| `MaxJeblick/llama2-0b-unit-test` | 4 | 0.002 |

## By recorded GPU

| GPU | Runs | Process-GPU hours |
|---|---:|---:|
| `NVIDIA A100-SXM4-80GB` | 222 | 36.314 |

## Interpretation

- This inventory measures completed run durations, not theoretical
  FLOPs or energy.
- It deliberately includes unsuccessful branches so compute is not
  understated by reporting only promoted positive results.
- Public model pretraining and upstream benchmark construction are
  outside the project-compute boundary.
- The machine-readable report lists every measured and excluded run.
