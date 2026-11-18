# GPU compute inventory

Process-GPU wall time of every experiment, reconstructed from the start and end timestamps saved
with each run configuration (`python scripts/audit_compute_inventory.py` rebuilds this file and
`COMPUTE_INVENTORY.json`).

## Headline

- Process-GPU hours, all experiments: 148.8
- Main experiments (`results/authoritykv/`): 36.3 hours over 222 run configurations
- Extended experiments (`runs/`): 112.5 hours over 192 runs
- Configurations without complete timestamps, not counted: 109

Every timestamp-complete configuration is counted, so the total is a lower bound on project
compute. Concurrent processes are counted separately; elapsed node time is smaller.

## By model

| Model | Runs | Process-GPU hours |
|---|---:|---:|
| `Qwen/Qwen2.5-7B-Instruct` | 292 | 89.757 |
| `01-ai/Yi-1.5-9B-Chat` | 39 | 25.006 |
| `mistralai/Mistral-7B-Instruct-v0.3` | 46 | 21.848 |
| `Qwen/Qwen2.5-14B-Instruct` | 29 | 12.148 |
| Smoke tests, audits, and detector probes | 8 | 0.041 |

## By recorded GPU

| GPU | Runs | Process-GPU hours |
|---|---:|---:|
| `NVIDIA A100 80GB PCIe` | 146 | 79.564 |
| `NVIDIA A100-SXM4-80GB` | 268 | 69.235 |

## Scope

- The inventory measures run durations, not FLOPs or energy.
- Public model pretraining and upstream benchmark construction are outside the project-compute
  boundary.
- `COMPUTE_INVENTORY.json` lists every counted and excluded configuration with its group.
