# ACL Main Official Sweep Summary

Data-quality status: **PASS**.

Complete run directories: 25/25.

## Method-level results

| Model | Method | KV keep | Feasible | ARR | Hierarchy success | Benign utility | Errors | Median prefill (s) | Median peak MB |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 01-ai/Yi-1.5-9B-Chat | `all_control_h2o_pin` | 20% | 420/500 | 1/320 | 319/320 | 100/100 | 0 | 0.7852 | 46481.0 |
| 01-ai/Yi-1.5-9B-Chat | `all_control_h2o_pin` | 40% | 500/500 | 1/400 | 399/400 | 100/100 | 0 | 0.7748 | 46575.8 |
| 01-ai/Yi-1.5-9B-Chat | `all_control_knorm_pin` | 20% | 420/500 | 49/320 | 271/320 | 100/100 | 0 | 0.3143 | 17194.3 |
| 01-ai/Yi-1.5-9B-Chat | `all_control_knorm_pin` | 40% | 500/500 | 18/400 | 382/400 | 100/100 | 0 | 0.3121 | 17251.7 |
| 01-ai/Yi-1.5-9B-Chat | `all_control_snapkv_pin` | 20% | 420/500 | 1/320 | 319/320 | 100/100 | 0 | 0.3375 | 17194.3 |
| 01-ai/Yi-1.5-9B-Chat | `all_control_snapkv_pin` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.3332 | 17251.7 |
| 01-ai/Yi-1.5-9B-Chat | `all_control_streaming_pin` | 20% | 420/500 | 82/320 | 238/320 | 100/100 | 0 | 0.3145 | 17194.3 |
| 01-ai/Yi-1.5-9B-Chat | `all_control_streaming_pin` | 40% | 500/500 | 41/400 | 359/400 | 100/100 | 0 | 0.3121 | 17251.7 |
| 01-ai/Yi-1.5-9B-Chat | `authority_h2o_detected_provenance` | 20% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.7892 | 46519.9 |
| 01-ai/Yi-1.5-9B-Chat | `authority_h2o_detected_provenance` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.7797 | 46575.8 |
| 01-ai/Yi-1.5-9B-Chat | `authority_knorm_detected_provenance` | 20% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.3185 | 17194.6 |
| 01-ai/Yi-1.5-9B-Chat | `authority_knorm_detected_provenance` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.3156 | 17251.7 |
| 01-ai/Yi-1.5-9B-Chat | `authority_snapkv_detected_provenance` | 20% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.3417 | 17194.6 |
| 01-ai/Yi-1.5-9B-Chat | `authority_snapkv_detected_provenance` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.3371 | 17251.7 |
| 01-ai/Yi-1.5-9B-Chat | `authority_streaming_detected_provenance` | 20% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.3186 | 17194.6 |
| 01-ai/Yi-1.5-9B-Chat | `authority_streaming_detected_provenance` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.3156 | 17251.7 |
| 01-ai/Yi-1.5-9B-Chat | `fullkv` | 100% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2921 | 17424.4 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_h2o` | 20% | 500/500 | 15/400 | 355/400 | 96/100 | 0 | 0.7686 | 46519.9 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_h2o` | 40% | 500/500 | 6/400 | 333/400 | 100/100 | 0 | 0.7593 | 46575.8 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_knorm` | 20% | 500/500 | 1/400 | 335/400 | 100/100 | 0 | 0.4991 | 17194.6 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_knorm` | 40% | 500/500 | 3/400 | 397/400 | 100/100 | 0 | 0.5093 | 17251.7 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_pyramid` | 20% | 500/500 | 6/400 | 369/400 | 100/100 | 0 | 0.5875 | 17194.6 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_pyramid` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.5784 | 17251.7 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_snapkv` | 20% | 500/500 | 6/400 | 369/400 | 100/100 | 0 | 0.5899 | 17194.6 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_snapkv` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.5767 | 17251.7 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_streaming` | 20% | 500/500 | 185/400 | 15/400 | 13/100 | 0 | 0.5083 | 17194.6 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_streaming` | 40% | 500/500 | 372/400 | 15/400 | 27/100 | 0 | 0.5117 | 17251.7 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_tova` | 20% | 500/500 | 3/400 | 394/400 | 100/100 | 0 | 0.5750 | 17194.6 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_tova` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.5839 | 17251.7 |
| 01-ai/Yi-1.5-9B-Chat | `system_h2o_pin` | 20% | 500/500 | 0/400 | 371/400 | 100/100 | 0 | 0.7839 | 46519.9 |
| 01-ai/Yi-1.5-9B-Chat | `system_h2o_pin` | 40% | 500/500 | 1/400 | 399/400 | 100/100 | 0 | 0.7741 | 46575.8 |
| 01-ai/Yi-1.5-9B-Chat | `system_knorm_pin` | 20% | 500/500 | 0/400 | 395/400 | 100/100 | 0 | 0.3141 | 17194.6 |
| 01-ai/Yi-1.5-9B-Chat | `system_knorm_pin` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.3117 | 17251.7 |
| 01-ai/Yi-1.5-9B-Chat | `system_snapkv_pin` | 20% | 500/500 | 0/400 | 399/400 | 100/100 | 0 | 0.3373 | 17194.6 |
| 01-ai/Yi-1.5-9B-Chat | `system_snapkv_pin` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.3325 | 17251.7 |
| 01-ai/Yi-1.5-9B-Chat | `system_streaming_pin` | 20% | 500/500 | 5/400 | 352/400 | 50/100 | 0 | 0.3143 | 17194.6 |
| 01-ai/Yi-1.5-9B-Chat | `system_streaming_pin` | 40% | 500/500 | 8/400 | 331/400 | 53/100 | 0 | 0.3116 | 17251.7 |
| Qwen/Qwen2.5-7B-Instruct | `authority_h2o_detected_provenance` | 10% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 0.9712 | 28190.8 |
| Qwen/Qwen2.5-7B-Instruct | `authority_h2o_detected_provenance` | 20% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 0.9688 | 28205.6 |
| Qwen/Qwen2.5-7B-Instruct | `authority_h2o_detected_provenance` | 40% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 0.9628 | 28235.2 |
| Qwen/Qwen2.5-7B-Instruct | `authority_h2o_detected_provenance` | 60% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 0.9664 | 28264.9 |
| Qwen/Qwen2.5-7B-Instruct | `authority_knorm_detected_provenance` | 10% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 1.3641 | 14937.0 |
| Qwen/Qwen2.5-7B-Instruct | `authority_knorm_detected_provenance` | 20% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 1.3642 | 14952.3 |
| Qwen/Qwen2.5-7B-Instruct | `authority_knorm_detected_provenance` | 40% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 1.3879 | 14995.1 |
| Qwen/Qwen2.5-7B-Instruct | `authority_knorm_detected_provenance` | 60% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 1.3805 | 15020.2 |
| Qwen/Qwen2.5-7B-Instruct | `authority_streaming_detected_provenance` | 10% | 120/120 | 0/100 | 100/100 | 19/20 | 0 | 1.3820 | 14937.0 |
| Qwen/Qwen2.5-7B-Instruct | `authority_streaming_detected_provenance` | 20% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 1.3869 | 14952.3 |
| Qwen/Qwen2.5-7B-Instruct | `authority_streaming_detected_provenance` | 40% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 1.3608 | 14995.1 |
| Qwen/Qwen2.5-7B-Instruct | `authority_streaming_detected_provenance` | 60% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 1.3676 | 15020.2 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | 10% | 120/120 | 32/100 | 24/100 | 18/20 | 0 | 0.8202 | 28190.8 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | 20% | 120/120 | 32/100 | 46/100 | 18/20 | 0 | 0.8379 | 28205.6 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | 40% | 120/120 | 35/100 | 65/100 | 1/20 | 0 | 0.8350 | 28235.2 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | 60% | 120/120 | 33/100 | 61/100 | 16/20 | 0 | 0.8322 | 28264.9 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | 10% | 120/120 | 0/100 | 52/100 | 3/20 | 0 | 0.7849 | 14937.0 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | 20% | 120/120 | 16/100 | 79/100 | 18/20 | 0 | 0.8012 | 14952.3 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | 40% | 120/120 | 6/100 | 94/100 | 20/20 | 0 | 0.7915 | 14995.1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | 60% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 0.7949 | 15020.2 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | 10% | 120/120 | 50/100 | 0/100 | 2/20 | 0 | 0.7835 | 14937.0 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | 20% | 120/120 | 50/100 | 0/100 | 3/20 | 0 | 0.7853 | 14952.3 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | 40% | 120/120 | 90/100 | 10/100 | 3/20 | 0 | 0.7828 | 14995.1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | 60% | 120/120 | 88/100 | 12/100 | 10/20 | 0 | 0.7853 | 15020.2 |
| Qwen/Qwen2.5-7B-Instruct | `all_control_h2o_pin` | 20% | 500/500 | 75/400 | 325/400 | 100/100 | 0 | 0.4167 | 28191.0 |
| Qwen/Qwen2.5-7B-Instruct | `all_control_h2o_pin` | 40% | 500/500 | 90/400 | 310/400 | 100/100 | 0 | 0.4104 | 28228.9 |
| Qwen/Qwen2.5-7B-Instruct | `all_control_knorm_pin` | 20% | 500/500 | 165/400 | 235/400 | 100/100 | 0 | 0.2065 | 14952.3 |
| Qwen/Qwen2.5-7B-Instruct | `all_control_knorm_pin` | 40% | 500/500 | 67/400 | 333/400 | 100/100 | 0 | 0.2038 | 14994.4 |
| Qwen/Qwen2.5-7B-Instruct | `all_control_snapkv_pin` | 20% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2170 | 14952.3 |
| Qwen/Qwen2.5-7B-Instruct | `all_control_snapkv_pin` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2141 | 14996.1 |
| Qwen/Qwen2.5-7B-Instruct | `all_control_streaming_pin` | 20% | 500/500 | 186/400 | 214/400 | 100/100 | 0 | 0.2067 | 14952.3 |
| Qwen/Qwen2.5-7B-Instruct | `all_control_streaming_pin` | 40% | 500/500 | 86/400 | 314/400 | 100/100 | 0 | 0.2039 | 14994.4 |
| Qwen/Qwen2.5-7B-Instruct | `authority_h2o_detected` | 20% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.4169 | 28191.0 |
| Qwen/Qwen2.5-7B-Instruct | `authority_h2o_detected` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.4105 | 28228.9 |
| Qwen/Qwen2.5-7B-Instruct | `authority_h2o_detected_provenance` | 20% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.4168 | 28191.0 |
| Qwen/Qwen2.5-7B-Instruct | `authority_h2o_detected_provenance` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.4105 | 28228.9 |
| Qwen/Qwen2.5-7B-Instruct | `authority_h2o_pin` | 20% | 500/500 | 52/400 | 348/400 | 100/100 | 0 | 0.4166 | 28191.0 |
| Qwen/Qwen2.5-7B-Instruct | `authority_h2o_pin` | 40% | 500/500 | 71/400 | 329/400 | 100/100 | 0 | 0.4101 | 28228.9 |
| Qwen/Qwen2.5-7B-Instruct | `authority_h2o_provenance` | 20% | 500/500 | 43/400 | 357/400 | 100/100 | 0 | 0.4170 | 28191.0 |
| Qwen/Qwen2.5-7B-Instruct | `authority_h2o_provenance` | 40% | 500/500 | 68/400 | 332/400 | 100/100 | 0 | 0.4105 | 28228.9 |
| Qwen/Qwen2.5-7B-Instruct | `authority_knorm_detected` | 20% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2085 | 14952.3 |
| Qwen/Qwen2.5-7B-Instruct | `authority_knorm_detected` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2059 | 14994.4 |
| Qwen/Qwen2.5-7B-Instruct | `authority_knorm_detected_provenance` | 20% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2086 | 14952.3 |
| Qwen/Qwen2.5-7B-Instruct | `authority_knorm_detected_provenance` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2058 | 14994.4 |
| Qwen/Qwen2.5-7B-Instruct | `authority_knorm_pin` | 20% | 500/500 | 1/400 | 399/400 | 100/100 | 0 | 0.2064 | 14952.3 |
| Qwen/Qwen2.5-7B-Instruct | `authority_knorm_pin` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2036 | 14994.4 |
| Qwen/Qwen2.5-7B-Instruct | `authority_knorm_provenance` | 20% | 500/500 | 1/400 | 399/400 | 100/100 | 0 | 0.2064 | 14952.3 |
| Qwen/Qwen2.5-7B-Instruct | `authority_knorm_provenance` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2036 | 14994.4 |
| Qwen/Qwen2.5-7B-Instruct | `authority_snapkv_detected` | 20% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2191 | 14952.3 |
| Qwen/Qwen2.5-7B-Instruct | `authority_snapkv_detected` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2161 | 14996.1 |
| Qwen/Qwen2.5-7B-Instruct | `authority_snapkv_detected_provenance` | 20% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2191 | 14952.3 |
| Qwen/Qwen2.5-7B-Instruct | `authority_snapkv_detected_provenance` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2161 | 14996.1 |
| Qwen/Qwen2.5-7B-Instruct | `authority_snapkv_pin` | 20% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2169 | 14952.3 |
| Qwen/Qwen2.5-7B-Instruct | `authority_snapkv_pin` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2140 | 14996.1 |
| Qwen/Qwen2.5-7B-Instruct | `authority_snapkv_provenance` | 20% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2168 | 14952.3 |
| Qwen/Qwen2.5-7B-Instruct | `authority_snapkv_provenance` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2140 | 14996.1 |
| Qwen/Qwen2.5-7B-Instruct | `authority_streaming_detected` | 20% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2087 | 14952.3 |
| Qwen/Qwen2.5-7B-Instruct | `authority_streaming_detected` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2059 | 14994.4 |
| Qwen/Qwen2.5-7B-Instruct | `authority_streaming_detected_provenance` | 20% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2088 | 14952.3 |
| Qwen/Qwen2.5-7B-Instruct | `authority_streaming_detected_provenance` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2058 | 14994.4 |
| Qwen/Qwen2.5-7B-Instruct | `authority_streaming_pin` | 20% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2066 | 14952.3 |
| Qwen/Qwen2.5-7B-Instruct | `authority_streaming_pin` | 40% | 500/500 | 29/400 | 371/400 | 100/100 | 0 | 0.2038 | 14994.4 |
| Qwen/Qwen2.5-7B-Instruct | `authority_streaming_provenance` | 20% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2065 | 14952.3 |
| Qwen/Qwen2.5-7B-Instruct | `authority_streaming_provenance` | 40% | 500/500 | 29/400 | 371/400 | 100/100 | 0 | 0.2037 | 14994.4 |
| Qwen/Qwen2.5-7B-Instruct | `fullkv` | 100% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.1918 | 15076.6 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | 20% | 500/500 | 118/400 | 199/400 | 97/100 | 0 | 0.4087 | 28191.0 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | 40% | 500/500 | 120/400 | 280/400 | 2/100 | 0 | 0.4027 | 28228.9 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | 20% | 500/500 | 80/400 | 297/400 | 94/100 | 0 | 0.1984 | 14952.3 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | 40% | 500/500 | 39/400 | 361/400 | 100/100 | 0 | 0.1958 | 14994.4 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_pyramid` | 20% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2096 | 14952.3 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_pyramid` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2070 | 14996.1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | 20% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2096 | 14952.3 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2069 | 14996.1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | 20% | 500/500 | 200/400 | 0/400 | 15/100 | 0 | 0.1984 | 14952.3 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | 40% | 500/500 | 361/400 | 39/400 | 11/100 | 0 | 0.1960 | 14994.4 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_tova` | 20% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2076 | 14952.3 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_tova` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2049 | 14994.4 |
| Qwen/Qwen2.5-7B-Instruct | `system_h2o_pin` | 20% | 500/500 | 116/400 | 278/400 | 50/100 | 0 | 0.4169 | 28191.0 |
| Qwen/Qwen2.5-7B-Instruct | `system_h2o_pin` | 40% | 500/500 | 109/400 | 289/400 | 50/100 | 0 | 0.4104 | 28228.9 |
| Qwen/Qwen2.5-7B-Instruct | `system_knorm_pin` | 20% | 500/500 | 39/400 | 302/400 | 83/100 | 0 | 0.2063 | 14952.3 |
| Qwen/Qwen2.5-7B-Instruct | `system_knorm_pin` | 40% | 500/500 | 28/400 | 372/400 | 100/100 | 0 | 0.2036 | 14994.4 |
| Qwen/Qwen2.5-7B-Instruct | `system_snapkv_pin` | 20% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2168 | 14952.3 |
| Qwen/Qwen2.5-7B-Instruct | `system_snapkv_pin` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2139 | 14996.1 |
| Qwen/Qwen2.5-7B-Instruct | `system_streaming_pin` | 20% | 500/500 | 16/400 | 315/400 | 50/100 | 0 | 0.2064 | 14952.3 |
| Qwen/Qwen2.5-7B-Instruct | `system_streaming_pin` | 40% | 500/500 | 35/400 | 349/400 | 50/100 | 0 | 0.2037 | 14994.4 |
| Qwen/Qwen2.5-7B-Instruct | `authority_h2o_detected_provenance` | 20% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 1.0797 | 27320.8 |
| Qwen/Qwen2.5-7B-Instruct | `authority_h2o_detected_provenance` | 40% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 1.0789 | 27349.5 |
| Qwen/Qwen2.5-7B-Instruct | `authority_knorm_detected_provenance` | 20% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 1.2015 | 14934.8 |
| Qwen/Qwen2.5-7B-Instruct | `authority_knorm_detected_provenance` | 40% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 1.2807 | 14964.5 |
| Qwen/Qwen2.5-7B-Instruct | `authority_streaming_detected_provenance` | 20% | 120/120 | 0/100 | 98/100 | 20/20 | 0 | 1.2050 | 14934.8 |
| Qwen/Qwen2.5-7B-Instruct | `authority_streaming_detected_provenance` | 40% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 1.2929 | 14964.5 |
| Qwen/Qwen2.5-7B-Instruct | `fullkv` | 100% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 0.6117 | 15053.7 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | 20% | 120/120 | 32/100 | 57/100 | 20/20 | 0 | 0.9002 | 27320.8 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | 40% | 120/120 | 33/100 | 67/100 | 1/20 | 0 | 0.8959 | 27349.5 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | 20% | 120/120 | 27/100 | 70/100 | 20/20 | 0 | 0.7866 | 14934.8 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | 40% | 120/120 | 20/100 | 80/100 | 20/20 | 0 | 0.7369 | 14964.5 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | 20% | 120/120 | 50/100 | 0/100 | 3/20 | 0 | 0.7865 | 14934.8 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | 40% | 120/120 | 89/100 | 11/100 | 3/20 | 0 | 0.7386 | 14964.5 |
| Qwen/Qwen2.5-7B-Instruct | `authority_h2o_detected_provenance` | 20% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 1.1031 | 27452.1 |
| Qwen/Qwen2.5-7B-Instruct | `authority_h2o_detected_provenance` | 40% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 1.1051 | 27480.9 |
| Qwen/Qwen2.5-7B-Instruct | `authority_knorm_detected_provenance` | 20% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 1.2853 | 14936.8 |
| Qwen/Qwen2.5-7B-Instruct | `authority_knorm_detected_provenance` | 40% | 120/120 | 0/100 | 99/100 | 20/20 | 0 | 1.2183 | 14966.7 |
| Qwen/Qwen2.5-7B-Instruct | `authority_streaming_detected_provenance` | 20% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 1.2914 | 14936.8 |
| Qwen/Qwen2.5-7B-Instruct | `authority_streaming_detected_provenance` | 40% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 1.2343 | 14966.7 |
| Qwen/Qwen2.5-7B-Instruct | `fullkv` | 100% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 0.5603 | 15056.4 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | 20% | 120/120 | 29/100 | 52/100 | 19/20 | 0 | 0.9035 | 27452.1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | 40% | 120/120 | 19/100 | 81/100 | 1/20 | 0 | 0.8960 | 27480.9 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | 20% | 120/120 | 6/100 | 93/100 | 19/20 | 0 | 0.7302 | 14936.8 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | 40% | 120/120 | 3/100 | 97/100 | 20/20 | 0 | 0.7522 | 14966.7 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | 20% | 120/120 | 50/100 | 0/100 | 0/20 | 0 | 0.7455 | 14936.8 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | 40% | 120/120 | 84/100 | 16/100 | 2/20 | 0 | 0.7392 | 14966.7 |
| Qwen/Qwen2.5-7B-Instruct | `authority_h2o_detected_provenance` | 20% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 1.0153 | 27320.8 |
| Qwen/Qwen2.5-7B-Instruct | `authority_h2o_detected_provenance` | 40% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 1.0055 | 27349.5 |
| Qwen/Qwen2.5-7B-Instruct | `authority_knorm_detected_provenance` | 20% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 1.2549 | 14934.8 |
| Qwen/Qwen2.5-7B-Instruct | `authority_knorm_detected_provenance` | 40% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 1.2196 | 14964.5 |
| Qwen/Qwen2.5-7B-Instruct | `authority_streaming_detected_provenance` | 20% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 1.2453 | 14934.8 |
| Qwen/Qwen2.5-7B-Instruct | `authority_streaming_detected_provenance` | 40% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 1.2259 | 14964.5 |
| Qwen/Qwen2.5-7B-Instruct | `fullkv` | 100% | 120/120 | 0/100 | 100/100 | 20/20 | 0 | 0.5991 | 15053.7 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | 20% | 120/120 | 50/100 | 41/100 | 19/20 | 0 | 0.8319 | 27320.8 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | 40% | 120/120 | 50/100 | 50/100 | 0/20 | 0 | 0.8366 | 27349.5 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | 20% | 120/120 | 28/100 | 70/100 | 18/20 | 0 | 0.7543 | 14934.8 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | 40% | 120/120 | 12/100 | 88/100 | 20/20 | 0 | 0.7817 | 14964.5 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | 20% | 120/120 | 50/100 | 0/100 | 2/20 | 0 | 0.7682 | 14934.8 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | 40% | 120/120 | 95/100 | 5/100 | 0/20 | 0 | 0.7947 | 14964.5 |
| mistralai/Mistral-7B-Instruct-v0.3 | `all_control_h2o_pin` | 20% | 420/500 | 0/320 | 320/320 | 100/100 | 0 | 0.5818 | 35365.5 |
| mistralai/Mistral-7B-Instruct-v0.3 | `all_control_h2o_pin` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.5820 | 35468.5 |
| mistralai/Mistral-7B-Instruct-v0.3 | `all_control_knorm_pin` | 20% | 420/500 | 0/320 | 320/320 | 100/100 | 0 | 0.2508 | 14264.5 |
| mistralai/Mistral-7B-Instruct-v0.3 | `all_control_knorm_pin` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2512 | 14342.6 |
| mistralai/Mistral-7B-Instruct-v0.3 | `all_control_snapkv_pin` | 20% | 420/500 | 0/320 | 320/320 | 100/100 | 0 | 0.2653 | 14264.5 |
| mistralai/Mistral-7B-Instruct-v0.3 | `all_control_snapkv_pin` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2657 | 14342.6 |
| mistralai/Mistral-7B-Instruct-v0.3 | `all_control_streaming_pin` | 20% | 420/500 | 26/320 | 294/320 | 100/100 | 0 | 0.2508 | 14264.5 |
| mistralai/Mistral-7B-Instruct-v0.3 | `all_control_streaming_pin` | 40% | 500/500 | 11/400 | 389/400 | 100/100 | 0 | 0.2511 | 14342.6 |
| mistralai/Mistral-7B-Instruct-v0.3 | `authority_h2o_detected_provenance` | 20% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.5819 | 35393.0 |
| mistralai/Mistral-7B-Instruct-v0.3 | `authority_h2o_detected_provenance` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.5818 | 35468.5 |
| mistralai/Mistral-7B-Instruct-v0.3 | `authority_knorm_detected_provenance` | 20% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2534 | 14264.7 |
| mistralai/Mistral-7B-Instruct-v0.3 | `authority_knorm_detected_provenance` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2535 | 14342.6 |
| mistralai/Mistral-7B-Instruct-v0.3 | `authority_snapkv_detected_provenance` | 20% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2681 | 14264.7 |
| mistralai/Mistral-7B-Instruct-v0.3 | `authority_snapkv_detected_provenance` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2682 | 14342.6 |
| mistralai/Mistral-7B-Instruct-v0.3 | `authority_streaming_detected_provenance` | 20% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2535 | 14264.7 |
| mistralai/Mistral-7B-Instruct-v0.3 | `authority_streaming_detected_provenance` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2536 | 14342.6 |
| mistralai/Mistral-7B-Instruct-v0.3 | `fullkv` | 100% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2383 | 14582.2 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_h2o` | 20% | 500/500 | 0/400 | 398/400 | 51/100 | 0 | 0.5725 | 35393.0 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_h2o` | 40% | 500/500 | 0/400 | 400/400 | 99/100 | 0 | 0.5729 | 35468.5 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_knorm` | 20% | 500/500 | 0/400 | 400/400 | 55/100 | 0 | 0.2426 | 14264.7 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_knorm` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2427 | 14342.6 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_pyramid` | 20% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2571 | 14264.8 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_pyramid` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2573 | 14342.7 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_snapkv` | 20% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2570 | 14264.7 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_snapkv` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2572 | 14342.6 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_streaming` | 20% | 500/500 | 183/400 | 13/400 | 12/100 | 0 | 0.2428 | 14264.7 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_streaming` | 40% | 500/500 | 372/400 | 27/400 | 14/100 | 0 | 0.2429 | 14342.6 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_tova` | 20% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2527 | 14264.7 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_tova` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2529 | 14342.6 |
| mistralai/Mistral-7B-Instruct-v0.3 | `system_h2o_pin` | 20% | 500/500 | 0/400 | 399/400 | 100/100 | 0 | 0.5816 | 35393.0 |
| mistralai/Mistral-7B-Instruct-v0.3 | `system_h2o_pin` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.5817 | 35468.5 |
| mistralai/Mistral-7B-Instruct-v0.3 | `system_knorm_pin` | 20% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2509 | 14264.7 |
| mistralai/Mistral-7B-Instruct-v0.3 | `system_knorm_pin` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2509 | 14342.6 |
| mistralai/Mistral-7B-Instruct-v0.3 | `system_snapkv_pin` | 20% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2653 | 14264.7 |
| mistralai/Mistral-7B-Instruct-v0.3 | `system_snapkv_pin` | 40% | 500/500 | 0/400 | 400/400 | 100/100 | 0 | 0.2655 | 14342.6 |
| mistralai/Mistral-7B-Instruct-v0.3 | `system_streaming_pin` | 20% | 500/500 | 35/400 | 279/400 | 50/100 | 0 | 0.2508 | 14264.7 |
| mistralai/Mistral-7B-Instruct-v0.3 | `system_streaming_pin` | 40% | 500/500 | 34/400 | 276/400 | 50/100 | 0 | 0.2509 | 14342.6 |

## Paired comparisons

| Model | Base | Comparison | KV keep | Base ARR | Comparison ARR | Relative reduction | Exact p | Holm p |
|---|---|---|---:|---:|---:|---:|---:|---:|
| 01-ai/Yi-1.5-9B-Chat | `kvpress_h2o` | `all_control_h2o_pin` | 20% | 15/320 | 1/320 | 93.3% | 0.000519 | 0.0285 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_h2o` | `all_control_h2o_pin` | 40% | 6/400 | 1/400 | 83.3% | 0.0625 | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_knorm` | `all_control_knorm_pin` | 20% | 1/320 | 49/320 | -4800.0% | 9.06e-14 | 7.25e-12 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_knorm` | `all_control_knorm_pin` | 40% | 3/400 | 18/400 | -500.0% | 0.00149 | 0.079 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_snapkv` | `all_control_snapkv_pin` | 20% | 6/320 | 1/320 | 83.3% | 0.0625 | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_snapkv` | `all_control_snapkv_pin` | 40% | 0/400 | 0/400 | n/a | 1 | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_streaming` | `all_control_streaming_pin` | 20% | 158/320 | 82/320 | 48.1% | 3.77e-18 | 3.39e-16 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_streaming` | `all_control_streaming_pin` | 40% | 372/400 | 41/400 | 89.0% | 4.57e-100 | 5.35e-98 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | 15/400 | 0/400 | 100.0% | 6.1e-05 | 0.0036 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | 6/400 | 0/400 | 100.0% | 0.0312 | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | 1/400 | 0/400 | 100.0% | 1 | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | 3/400 | 0/400 | 100.0% | 0.25 | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_snapkv` | `authority_snapkv_detected_provenance` | 20% | 6/400 | 0/400 | 100.0% | 0.0312 | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_snapkv` | `authority_snapkv_detected_provenance` | 40% | 0/400 | 0/400 | n/a | 1 | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | 185/400 | 0/400 | 100.0% | 4.08e-56 | 4.49e-54 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | 372/400 | 0/400 | 100.0% | 2.08e-112 | 2.62e-110 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_h2o` | `system_h2o_pin` | 20% | 15/400 | 0/400 | 100.0% | 6.1e-05 | 0.0036 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_h2o` | `system_h2o_pin` | 40% | 6/400 | 1/400 | 83.3% | 0.0625 | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_knorm` | `system_knorm_pin` | 20% | 1/400 | 0/400 | 100.0% | 1 | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_knorm` | `system_knorm_pin` | 40% | 3/400 | 0/400 | 100.0% | 0.25 | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_snapkv` | `system_snapkv_pin` | 20% | 6/400 | 0/400 | 100.0% | 0.0312 | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_snapkv` | `system_snapkv_pin` | 40% | 0/400 | 0/400 | n/a | 1 | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_streaming` | `system_streaming_pin` | 20% | 185/400 | 5/400 | 97.3% | 2.56e-48 | 2.77e-46 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_streaming` | `system_streaming_pin` | 40% | 372/400 | 8/400 | 97.8% | 5.32e-110 | 6.6e-108 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 10% | 32/100 | 0/100 | 100.0% | 4.66e-10 | 3.21e-08 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | 32/100 | 0/100 | 100.0% | 4.66e-10 | 3.21e-08 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | 35/100 | 0/100 | 100.0% | 5.82e-11 | 4.19e-09 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 60% | 33/100 | 0/100 | 100.0% | 2.33e-10 | 1.65e-08 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 10% | 0/100 | 0/100 | n/a | 1 | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | 16/100 | 0/100 | 100.0% | 3.05e-05 | 0.00183 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | 6/100 | 0/100 | 100.0% | 0.0312 | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 60% | 0/100 | 0/100 | n/a | 1 | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 10% | 50/100 | 0/100 | 100.0% | 1.78e-15 | 1.58e-13 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | 50/100 | 0/100 | 100.0% | 1.78e-15 | 1.58e-13 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | 90/100 | 0/100 | 100.0% | 1.62e-27 | 1.62e-25 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 60% | 88/100 | 0/100 | 100.0% | 6.46e-27 | 6.33e-25 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `all_control_h2o_pin` | 20% | 118/400 | 75/400 | 36.4% | 1.68e-07 | 1.06e-05 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `all_control_h2o_pin` | 40% | 120/400 | 90/400 | 25.0% | 0.000535 | 0.0289 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `all_control_knorm_pin` | 20% | 80/400 | 165/400 | -106.2% | 2.3e-14 | 1.86e-12 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `all_control_knorm_pin` | 40% | 39/400 | 67/400 | -71.8% | 0.000394 | 0.0225 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `all_control_snapkv_pin` | 20% | 0/400 | 0/400 | n/a | 1 | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `all_control_snapkv_pin` | 40% | 0/400 | 0/400 | n/a | 1 | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `all_control_streaming_pin` | 20% | 200/400 | 186/400 | 7.0% | 0.184 | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `all_control_streaming_pin` | 40% | 361/400 | 86/400 | 76.2% | 3.29e-83 | 3.79e-81 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected` | 20% | 118/400 | 0/400 | 100.0% | 6.02e-36 | 6.26e-34 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected` | 40% | 120/400 | 0/400 | 100.0% | 1.5e-36 | 1.59e-34 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | 118/400 | 0/400 | 100.0% | 6.02e-36 | 6.26e-34 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | 120/400 | 0/400 | 100.0% | 1.5e-36 | 1.59e-34 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_pin` | 20% | 118/400 | 52/400 | 55.9% | 1.85e-15 | 1.58e-13 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_pin` | 40% | 120/400 | 71/400 | 40.8% | 1.91e-11 | 1.39e-09 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_provenance` | 20% | 118/400 | 43/400 | 63.6% | 1.81e-18 | 1.64e-16 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_provenance` | 40% | 120/400 | 68/400 | 43.3% | 3.07e-12 | 2.42e-10 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected` | 20% | 80/400 | 0/400 | 100.0% | 1.65e-24 | 1.57e-22 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected` | 40% | 39/400 | 0/400 | 100.0% | 3.64e-12 | 2.84e-10 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | 80/400 | 0/400 | 100.0% | 1.65e-24 | 1.57e-22 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | 39/400 | 0/400 | 100.0% | 3.64e-12 | 2.84e-10 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_pin` | 20% | 80/400 | 1/400 | 98.8% | 3.31e-24 | 3.08e-22 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_pin` | 40% | 39/400 | 0/400 | 100.0% | 3.64e-12 | 2.84e-10 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_provenance` | 20% | 80/400 | 1/400 | 98.8% | 3.31e-24 | 3.08e-22 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_provenance` | 40% | 39/400 | 0/400 | 100.0% | 3.64e-12 | 2.84e-10 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `authority_snapkv_detected` | 20% | 0/400 | 0/400 | n/a | 1 | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `authority_snapkv_detected` | 40% | 0/400 | 0/400 | n/a | 1 | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `authority_snapkv_detected_provenance` | 20% | 0/400 | 0/400 | n/a | 1 | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `authority_snapkv_detected_provenance` | 40% | 0/400 | 0/400 | n/a | 1 | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `authority_snapkv_pin` | 20% | 0/400 | 0/400 | n/a | 1 | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `authority_snapkv_pin` | 40% | 0/400 | 0/400 | n/a | 1 | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `authority_snapkv_provenance` | 20% | 0/400 | 0/400 | n/a | 1 | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `authority_snapkv_provenance` | 40% | 0/400 | 0/400 | n/a | 1 | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected` | 20% | 200/400 | 0/400 | 100.0% | 1.24e-60 | 1.42e-58 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected` | 40% | 361/400 | 0/400 | 100.0% | 4.26e-109 | 5.24e-107 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | 200/400 | 0/400 | 100.0% | 1.24e-60 | 1.42e-58 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | 361/400 | 0/400 | 100.0% | 4.26e-109 | 5.24e-107 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_pin` | 20% | 200/400 | 0/400 | 100.0% | 1.24e-60 | 1.42e-58 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_pin` | 40% | 361/400 | 29/400 | 92.0% | 2.29e-100 | 2.72e-98 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_provenance` | 20% | 200/400 | 0/400 | 100.0% | 1.24e-60 | 1.42e-58 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_provenance` | 40% | 361/400 | 29/400 | 92.0% | 2.29e-100 | 2.72e-98 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `system_h2o_pin` | 20% | 118/400 | 116/400 | 1.7% | 0.916 | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `system_h2o_pin` | 40% | 120/400 | 109/400 | 9.2% | 0.235 | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `system_knorm_pin` | 20% | 80/400 | 39/400 | 51.2% | 1e-11 | 7.4e-10 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `system_knorm_pin` | 40% | 39/400 | 28/400 | 28.2% | 0.00739 | 0.384 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `system_snapkv_pin` | 20% | 0/400 | 0/400 | n/a | 1 | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `system_snapkv_pin` | 40% | 0/400 | 0/400 | n/a | 1 | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `system_streaming_pin` | 20% | 200/400 | 16/400 | 92.0% | 1.25e-41 | 1.34e-39 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `system_streaming_pin` | 40% | 361/400 | 35/400 | 90.3% | 1.46e-98 | 1.7e-96 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | 32/100 | 0/100 | 100.0% | 4.66e-10 | 3.21e-08 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | 33/100 | 0/100 | 100.0% | 2.33e-10 | 1.65e-08 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | 27/100 | 0/100 | 100.0% | 1.49e-08 | 9.54e-07 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | 20/100 | 0/100 | 100.0% | 1.91e-06 | 0.000118 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | 50/100 | 0/100 | 100.0% | 1.78e-15 | 1.58e-13 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | 89/100 | 0/100 | 100.0% | 3.23e-27 | 3.2e-25 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | 29/100 | 0/100 | 100.0% | 3.73e-09 | 2.46e-07 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | 19/100 | 0/100 | 100.0% | 3.81e-06 | 0.000233 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | 6/100 | 0/100 | 100.0% | 0.0312 | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | 3/100 | 0/100 | 100.0% | 0.25 | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | 50/100 | 0/100 | 100.0% | 1.78e-15 | 1.58e-13 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | 84/100 | 0/100 | 100.0% | 1.03e-25 | 1e-23 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | 50/100 | 0/100 | 100.0% | 1.78e-15 | 1.58e-13 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | 50/100 | 0/100 | 100.0% | 1.78e-15 | 1.58e-13 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | 28/100 | 0/100 | 100.0% | 7.45e-09 | 4.84e-07 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | 12/100 | 0/100 | 100.0% | 0.000488 | 0.0273 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | 50/100 | 0/100 | 100.0% | 1.78e-15 | 1.58e-13 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | 95/100 | 0/100 | 100.0% | 5.05e-29 | 5.1e-27 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_h2o` | `all_control_h2o_pin` | 20% | 0/320 | 0/320 | n/a | 1 | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_h2o` | `all_control_h2o_pin` | 40% | 0/400 | 0/400 | n/a | 1 | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_knorm` | `all_control_knorm_pin` | 20% | 0/320 | 0/320 | n/a | 1 | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_knorm` | `all_control_knorm_pin` | 40% | 0/400 | 0/400 | n/a | 1 | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_snapkv` | `all_control_snapkv_pin` | 20% | 0/320 | 0/320 | n/a | 1 | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_snapkv` | `all_control_snapkv_pin` | 40% | 0/400 | 0/400 | n/a | 1 | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_streaming` | `all_control_streaming_pin` | 20% | 145/320 | 26/320 | 82.1% | 1.43e-33 | 1.46e-31 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_streaming` | `all_control_streaming_pin` | 40% | 372/400 | 11/400 | 97.0% | 3.87e-107 | 4.69e-105 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | 0/400 | 0/400 | n/a | 1 | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | 0/400 | 0/400 | n/a | 1 | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | 0/400 | 0/400 | n/a | 1 | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | 0/400 | 0/400 | n/a | 1 | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_snapkv` | `authority_snapkv_detected_provenance` | 20% | 0/400 | 0/400 | n/a | 1 | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_snapkv` | `authority_snapkv_detected_provenance` | 40% | 0/400 | 0/400 | n/a | 1 | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | 183/400 | 0/400 | 100.0% | 1.63e-55 | 1.78e-53 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | 372/400 | 0/400 | 100.0% | 2.08e-112 | 2.62e-110 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_h2o` | `system_h2o_pin` | 20% | 0/400 | 0/400 | n/a | 1 | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_h2o` | `system_h2o_pin` | 40% | 0/400 | 0/400 | n/a | 1 | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_knorm` | `system_knorm_pin` | 20% | 0/400 | 0/400 | n/a | 1 | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_knorm` | `system_knorm_pin` | 40% | 0/400 | 0/400 | n/a | 1 | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_snapkv` | `system_snapkv_pin` | 20% | 0/400 | 0/400 | n/a | 1 | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_snapkv` | `system_snapkv_pin` | 40% | 0/400 | 0/400 | n/a | 1 | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_streaming` | `system_streaming_pin` | 20% | 183/400 | 35/400 | 80.9% | 2.22e-25 | 2.13e-23 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_streaming` | `system_streaming_pin` | 40% | 372/400 | 34/400 | 90.9% | 3.57e-102 | 4.29e-100 |

## Paired secondary endpoints

These endpoints use a separate global Holm family; the registered authority-reversal family above is unchanged.

| Model | Base | Comparison | KV keep | Endpoint | Scope | Base | Comparison | Delta | Holm p |
|---|---|---|---:|---|---|---:|---:|---:|---:|
| 01-ai/Yi-1.5-9B-Chat | `kvpress_h2o` | `all_control_h2o_pin` | 20% | hierarchy_success | conflict | 275/320 | 319/320 | +13.8% | 3.47e-10 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_h2o` | `all_control_h2o_pin` | 20% | benign_utility | benign | 96/100 | 100/100 | +4.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_h2o` | `all_control_h2o_pin` | 20% | strict_json | all_fullkv_correct | 420/420 | 420/420 | +0.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_h2o` | `all_control_h2o_pin` | 40% | hierarchy_success | conflict | 333/400 | 399/400 | +16.5% | 7.62e-18 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_h2o` | `all_control_h2o_pin` | 40% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_h2o` | `all_control_h2o_pin` | 40% | strict_json | all_fullkv_correct | 495/500 | 500/500 | +1.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_knorm` | `all_control_knorm_pin` | 20% | hierarchy_success | conflict | 255/320 | 271/320 | +5.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_knorm` | `all_control_knorm_pin` | 20% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_knorm` | `all_control_knorm_pin` | 20% | strict_json | all_fullkv_correct | 420/420 | 420/420 | +0.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_knorm` | `all_control_knorm_pin` | 40% | hierarchy_success | conflict | 397/400 | 382/400 | -3.8% | 0.316 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_knorm` | `all_control_knorm_pin` | 40% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_knorm` | `all_control_knorm_pin` | 40% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_snapkv` | `all_control_snapkv_pin` | 20% | hierarchy_success | conflict | 289/320 | 319/320 | +9.4% | 4.58e-07 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_snapkv` | `all_control_snapkv_pin` | 20% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_snapkv` | `all_control_snapkv_pin` | 20% | strict_json | all_fullkv_correct | 420/420 | 420/420 | +0.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_snapkv` | `all_control_snapkv_pin` | 40% | hierarchy_success | conflict | 400/400 | 400/400 | +0.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_snapkv` | `all_control_snapkv_pin` | 40% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_snapkv` | `all_control_snapkv_pin` | 40% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_streaming` | `all_control_streaming_pin` | 20% | hierarchy_success | conflict | 2/320 | 238/320 | +73.8% | 3.72e-67 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_streaming` | `all_control_streaming_pin` | 20% | benign_utility | benign | 13/100 | 100/100 | +87.0% | 3.93e-24 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_streaming` | `all_control_streaming_pin` | 20% | strict_json | all_fullkv_correct | 174/420 | 418/420 | +58.1% | 2.45e-71 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_streaming` | `all_control_streaming_pin` | 40% | hierarchy_success | conflict | 15/400 | 359/400 | +86.0% | 2.05e-101 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_streaming` | `all_control_streaming_pin` | 40% | benign_utility | benign | 27/100 | 100/100 | +73.0% | 6.12e-20 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_streaming` | `all_control_streaming_pin` | 40% | strict_json | all_fullkv_correct | 427/500 | 500/500 | +14.6% | 6.12e-20 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | hierarchy_success | conflict | 355/400 | 400/400 | +11.2% | 1.51e-11 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | benign_utility | benign | 96/100 | 100/100 | +4.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | hierarchy_success | conflict | 333/400 | 400/400 | +16.8% | 3.82e-18 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | strict_json | all_fullkv_correct | 495/500 | 500/500 | +1.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | hierarchy_success | conflict | 335/400 | 400/400 | +16.2% | 1.51e-17 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | hierarchy_success | conflict | 397/400 | 400/400 | +0.8% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_snapkv` | `authority_snapkv_detected_provenance` | 20% | hierarchy_success | conflict | 369/400 | 400/400 | +7.8% | 2.3e-07 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_snapkv` | `authority_snapkv_detected_provenance` | 20% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_snapkv` | `authority_snapkv_detected_provenance` | 20% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_snapkv` | `authority_snapkv_detected_provenance` | 40% | hierarchy_success | conflict | 400/400 | 400/400 | +0.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_snapkv` | `authority_snapkv_detected_provenance` | 40% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_snapkv` | `authority_snapkv_detected_provenance` | 40% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | hierarchy_success | conflict | 15/400 | 400/400 | +96.2% | 9.47e-114 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | benign_utility | benign | 13/100 | 100/100 | +87.0% | 3.93e-24 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | strict_json | all_fullkv_correct | 214/500 | 500/500 | +57.2% | 5.66e-84 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | hierarchy_success | conflict | 15/400 | 400/400 | +96.2% | 9.47e-114 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | benign_utility | benign | 27/100 | 100/100 | +73.0% | 6.12e-20 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | strict_json | all_fullkv_correct | 427/500 | 500/500 | +14.6% | 6.12e-20 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_h2o` | `system_h2o_pin` | 20% | hierarchy_success | conflict | 355/400 | 371/400 | +4.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_h2o` | `system_h2o_pin` | 20% | benign_utility | benign | 96/100 | 100/100 | +4.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_h2o` | `system_h2o_pin` | 20% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_h2o` | `system_h2o_pin` | 40% | hierarchy_success | conflict | 333/400 | 399/400 | +16.5% | 7.62e-18 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_h2o` | `system_h2o_pin` | 40% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_h2o` | `system_h2o_pin` | 40% | strict_json | all_fullkv_correct | 495/500 | 500/500 | +1.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_knorm` | `system_knorm_pin` | 20% | hierarchy_success | conflict | 335/400 | 395/400 | +15.0% | 4.77e-16 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_knorm` | `system_knorm_pin` | 20% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_knorm` | `system_knorm_pin` | 20% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_knorm` | `system_knorm_pin` | 40% | hierarchy_success | conflict | 397/400 | 400/400 | +0.8% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_knorm` | `system_knorm_pin` | 40% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_knorm` | `system_knorm_pin` | 40% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_snapkv` | `system_snapkv_pin` | 20% | hierarchy_success | conflict | 369/400 | 399/400 | +7.5% | 4.58e-07 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_snapkv` | `system_snapkv_pin` | 20% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_snapkv` | `system_snapkv_pin` | 20% | strict_json | all_fullkv_correct | 500/500 | 499/500 | -0.2% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_snapkv` | `system_snapkv_pin` | 40% | hierarchy_success | conflict | 400/400 | 400/400 | +0.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_snapkv` | `system_snapkv_pin` | 40% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_snapkv` | `system_snapkv_pin` | 40% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_streaming` | `system_streaming_pin` | 20% | hierarchy_success | conflict | 15/400 | 352/400 | +84.2% | 2.21e-97 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_streaming` | `system_streaming_pin` | 20% | benign_utility | benign | 13/100 | 50/100 | +37.0% | 5.66e-05 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_streaming` | `system_streaming_pin` | 20% | strict_json | all_fullkv_correct | 214/500 | 500/500 | +57.2% | 5.66e-84 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_streaming` | `system_streaming_pin` | 40% | hierarchy_success | conflict | 15/400 | 331/400 | +79.0% | 5.44e-93 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_streaming` | `system_streaming_pin` | 40% | benign_utility | benign | 27/100 | 53/100 | +26.0% | 0.048 |
| 01-ai/Yi-1.5-9B-Chat | `kvpress_streaming` | `system_streaming_pin` | 40% | strict_json | all_fullkv_correct | 427/500 | 500/500 | +14.6% | 6.12e-20 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 10% | hierarchy_success | conflict | 24/100 | 100/100 | +76.0% | 7.68e-21 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 10% | benign_utility | benign | 18/20 | 20/20 | +10.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 10% | strict_json | all_fullkv_correct | 86/120 | 120/120 | +28.3% | 2.9e-08 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | hierarchy_success | conflict | 46/100 | 100/100 | +54.0% | 3.03e-14 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | benign_utility | benign | 18/20 | 20/20 | +10.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | strict_json | all_fullkv_correct | 118/120 | 120/120 | +1.7% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | hierarchy_success | conflict | 65/100 | 100/100 | +35.0% | 1.46e-08 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | benign_utility | benign | 1/20 | 20/20 | +95.0% | 0.00087 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | strict_json | all_fullkv_correct | 120/120 | 120/120 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 60% | hierarchy_success | conflict | 61/100 | 100/100 | +39.0% | 9.39e-10 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 60% | benign_utility | benign | 16/20 | 20/20 | +20.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 60% | strict_json | all_fullkv_correct | 120/120 | 120/120 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 10% | hierarchy_success | conflict | 52/100 | 100/100 | +48.0% | 1.9e-12 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 10% | benign_utility | benign | 3/20 | 20/20 | +85.0% | 0.00339 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 10% | strict_json | all_fullkv_correct | 119/120 | 120/120 | +0.8% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | hierarchy_success | conflict | 79/100 | 100/100 | +21.0% | 0.000226 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | benign_utility | benign | 18/20 | 20/20 | +10.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | strict_json | all_fullkv_correct | 120/120 | 120/120 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | hierarchy_success | conflict | 94/100 | 100/100 | +6.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | benign_utility | benign | 20/20 | 20/20 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | strict_json | all_fullkv_correct | 120/120 | 120/120 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 60% | hierarchy_success | conflict | 100/100 | 100/100 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 60% | benign_utility | benign | 20/20 | 20/20 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 60% | strict_json | all_fullkv_correct | 120/120 | 120/120 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 10% | hierarchy_success | conflict | 0/100 | 100/100 | +100.0% | 5.22e-28 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 10% | benign_utility | benign | 2/20 | 19/20 | +85.0% | 0.00339 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 10% | strict_json | all_fullkv_correct | 50/120 | 119/120 | +57.5% | 1.7e-17 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | hierarchy_success | conflict | 0/100 | 100/100 | +100.0% | 5.22e-28 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | benign_utility | benign | 3/20 | 20/20 | +85.0% | 0.00339 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | strict_json | all_fullkv_correct | 51/120 | 120/120 | +57.5% | 9.59e-19 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | hierarchy_success | conflict | 10/100 | 100/100 | +90.0% | 5.07e-25 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | benign_utility | benign | 3/20 | 20/20 | +85.0% | 0.00339 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | strict_json | all_fullkv_correct | 100/120 | 120/120 | +16.7% | 0.00045 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 60% | hierarchy_success | conflict | 12/100 | 100/100 | +88.0% | 1.98e-24 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 60% | benign_utility | benign | 10/20 | 20/20 | +50.0% | 0.412 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 60% | strict_json | all_fullkv_correct | 110/120 | 120/120 | +8.3% | 0.412 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `all_control_h2o_pin` | 20% | hierarchy_success | conflict | 199/400 | 325/400 | +31.5% | 4.09e-31 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `all_control_h2o_pin` | 20% | benign_utility | benign | 97/100 | 100/100 | +3.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `all_control_h2o_pin` | 20% | strict_json | all_fullkv_correct | 496/500 | 500/500 | +0.8% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `all_control_h2o_pin` | 40% | hierarchy_success | conflict | 280/400 | 310/400 | +7.5% | 0.114 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `all_control_h2o_pin` | 40% | benign_utility | benign | 2/100 | 100/100 | +98.0% | 2.03e-27 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `all_control_h2o_pin` | 40% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `all_control_knorm_pin` | 20% | hierarchy_success | conflict | 297/400 | 235/400 | -15.5% | 1.55e-06 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `all_control_knorm_pin` | 20% | benign_utility | benign | 94/100 | 100/100 | +6.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `all_control_knorm_pin` | 20% | strict_json | all_fullkv_correct | 498/500 | 500/500 | +0.4% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `all_control_knorm_pin` | 40% | hierarchy_success | conflict | 361/400 | 333/400 | -7.0% | 0.0847 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `all_control_knorm_pin` | 40% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `all_control_knorm_pin` | 40% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `all_control_snapkv_pin` | 20% | hierarchy_success | conflict | 400/400 | 400/400 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `all_control_snapkv_pin` | 20% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `all_control_snapkv_pin` | 20% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `all_control_snapkv_pin` | 40% | hierarchy_success | conflict | 400/400 | 400/400 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `all_control_snapkv_pin` | 40% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `all_control_snapkv_pin` | 40% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `all_control_streaming_pin` | 20% | hierarchy_success | conflict | 0/400 | 214/400 | +53.5% | 2.61e-62 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `all_control_streaming_pin` | 20% | benign_utility | benign | 15/100 | 100/100 | +85.0% | 1.54e-23 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `all_control_streaming_pin` | 20% | strict_json | all_fullkv_correct | 202/500 | 500/500 | +59.6% | 1.41e-87 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `all_control_streaming_pin` | 40% | hierarchy_success | conflict | 39/400 | 314/400 | +68.8% | 1.15e-80 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `all_control_streaming_pin` | 40% | benign_utility | benign | 11/100 | 100/100 | +89.0% | 1.01e-24 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `all_control_streaming_pin` | 40% | strict_json | all_fullkv_correct | 401/500 | 500/500 | +19.8% | 1.03e-27 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected` | 20% | hierarchy_success | conflict | 199/400 | 400/400 | +50.2% | 2.13e-58 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected` | 20% | benign_utility | benign | 97/100 | 100/100 | +3.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected` | 20% | strict_json | all_fullkv_correct | 496/500 | 500/500 | +0.8% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected` | 40% | hierarchy_success | conflict | 280/400 | 400/400 | +30.0% | 5.09e-34 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected` | 40% | benign_utility | benign | 2/100 | 100/100 | +98.0% | 2.03e-27 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected` | 40% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | hierarchy_success | conflict | 199/400 | 400/400 | +50.2% | 2.13e-58 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | benign_utility | benign | 97/100 | 100/100 | +3.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | strict_json | all_fullkv_correct | 496/500 | 500/500 | +0.8% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | hierarchy_success | conflict | 280/400 | 400/400 | +30.0% | 5.09e-34 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | benign_utility | benign | 2/100 | 100/100 | +98.0% | 2.03e-27 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_pin` | 20% | hierarchy_success | conflict | 199/400 | 348/400 | +37.2% | 9.5e-43 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_pin` | 20% | benign_utility | benign | 97/100 | 100/100 | +3.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_pin` | 20% | strict_json | all_fullkv_correct | 496/500 | 500/500 | +0.8% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_pin` | 40% | hierarchy_success | conflict | 280/400 | 329/400 | +12.2% | 4.8e-09 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_pin` | 40% | benign_utility | benign | 2/100 | 100/100 | +98.0% | 2.03e-27 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_pin` | 40% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_provenance` | 20% | hierarchy_success | conflict | 199/400 | 357/400 | +39.5% | 1.86e-45 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_provenance` | 20% | benign_utility | benign | 97/100 | 100/100 | +3.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_provenance` | 20% | strict_json | all_fullkv_correct | 496/500 | 500/500 | +0.8% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_provenance` | 40% | hierarchy_success | conflict | 280/400 | 332/400 | +13.0% | 7.94e-10 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_provenance` | 40% | benign_utility | benign | 2/100 | 100/100 | +98.0% | 2.03e-27 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_provenance` | 40% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected` | 20% | hierarchy_success | conflict | 297/400 | 400/400 | +25.8% | 6.61e-29 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected` | 20% | benign_utility | benign | 94/100 | 100/100 | +6.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected` | 20% | strict_json | all_fullkv_correct | 498/500 | 500/500 | +0.4% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected` | 40% | hierarchy_success | conflict | 361/400 | 400/400 | +9.8% | 9.39e-10 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected` | 40% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected` | 40% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | hierarchy_success | conflict | 297/400 | 400/400 | +25.8% | 6.61e-29 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | benign_utility | benign | 94/100 | 100/100 | +6.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | strict_json | all_fullkv_correct | 498/500 | 500/500 | +0.4% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | hierarchy_success | conflict | 361/400 | 400/400 | +9.8% | 9.39e-10 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_pin` | 20% | hierarchy_success | conflict | 297/400 | 399/400 | +25.5% | 1.31e-28 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_pin` | 20% | benign_utility | benign | 94/100 | 100/100 | +6.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_pin` | 20% | strict_json | all_fullkv_correct | 498/500 | 500/500 | +0.4% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_pin` | 40% | hierarchy_success | conflict | 361/400 | 400/400 | +9.8% | 9.39e-10 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_pin` | 40% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_pin` | 40% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_provenance` | 20% | hierarchy_success | conflict | 297/400 | 399/400 | +25.5% | 1.31e-28 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_provenance` | 20% | benign_utility | benign | 94/100 | 100/100 | +6.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_provenance` | 20% | strict_json | all_fullkv_correct | 498/500 | 500/500 | +0.4% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_provenance` | 40% | hierarchy_success | conflict | 361/400 | 400/400 | +9.8% | 9.39e-10 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_provenance` | 40% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_provenance` | 40% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `authority_snapkv_detected` | 20% | hierarchy_success | conflict | 400/400 | 400/400 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `authority_snapkv_detected` | 20% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `authority_snapkv_detected` | 20% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `authority_snapkv_detected` | 40% | hierarchy_success | conflict | 400/400 | 400/400 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `authority_snapkv_detected` | 40% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `authority_snapkv_detected` | 40% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `authority_snapkv_detected_provenance` | 20% | hierarchy_success | conflict | 400/400 | 400/400 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `authority_snapkv_detected_provenance` | 20% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `authority_snapkv_detected_provenance` | 20% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `authority_snapkv_detected_provenance` | 40% | hierarchy_success | conflict | 400/400 | 400/400 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `authority_snapkv_detected_provenance` | 40% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `authority_snapkv_detected_provenance` | 40% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `authority_snapkv_pin` | 20% | hierarchy_success | conflict | 400/400 | 400/400 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `authority_snapkv_pin` | 20% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `authority_snapkv_pin` | 20% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `authority_snapkv_pin` | 40% | hierarchy_success | conflict | 400/400 | 400/400 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `authority_snapkv_pin` | 40% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `authority_snapkv_pin` | 40% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `authority_snapkv_provenance` | 20% | hierarchy_success | conflict | 400/400 | 400/400 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `authority_snapkv_provenance` | 20% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `authority_snapkv_provenance` | 20% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `authority_snapkv_provenance` | 40% | hierarchy_success | conflict | 400/400 | 400/400 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `authority_snapkv_provenance` | 40% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `authority_snapkv_provenance` | 40% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected` | 20% | hierarchy_success | conflict | 0/400 | 400/400 | +100.0% | 2.93e-118 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected` | 20% | benign_utility | benign | 15/100 | 100/100 | +85.0% | 1.54e-23 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected` | 20% | strict_json | all_fullkv_correct | 202/500 | 500/500 | +59.6% | 1.41e-87 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected` | 40% | hierarchy_success | conflict | 39/400 | 400/400 | +90.2% | 1.58e-106 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected` | 40% | benign_utility | benign | 11/100 | 100/100 | +89.0% | 1.01e-24 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected` | 40% | strict_json | all_fullkv_correct | 401/500 | 500/500 | +19.8% | 1.03e-27 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | hierarchy_success | conflict | 0/400 | 400/400 | +100.0% | 2.93e-118 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | benign_utility | benign | 15/100 | 100/100 | +85.0% | 1.54e-23 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | strict_json | all_fullkv_correct | 202/500 | 500/500 | +59.6% | 1.41e-87 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | hierarchy_success | conflict | 39/400 | 400/400 | +90.2% | 1.58e-106 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | benign_utility | benign | 11/100 | 100/100 | +89.0% | 1.01e-24 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | strict_json | all_fullkv_correct | 401/500 | 500/500 | +19.8% | 1.03e-27 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_pin` | 20% | hierarchy_success | conflict | 0/400 | 400/400 | +100.0% | 2.93e-118 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_pin` | 20% | benign_utility | benign | 15/100 | 100/100 | +85.0% | 1.54e-23 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_pin` | 20% | strict_json | all_fullkv_correct | 202/500 | 500/500 | +59.6% | 1.41e-87 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_pin` | 40% | hierarchy_success | conflict | 39/400 | 371/400 | +83.0% | 8.37e-98 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_pin` | 40% | benign_utility | benign | 11/100 | 100/100 | +89.0% | 1.01e-24 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_pin` | 40% | strict_json | all_fullkv_correct | 401/500 | 500/500 | +19.8% | 1.03e-27 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_provenance` | 20% | hierarchy_success | conflict | 0/400 | 400/400 | +100.0% | 2.93e-118 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_provenance` | 20% | benign_utility | benign | 15/100 | 100/100 | +85.0% | 1.54e-23 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_provenance` | 20% | strict_json | all_fullkv_correct | 202/500 | 500/500 | +59.6% | 1.41e-87 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_provenance` | 40% | hierarchy_success | conflict | 39/400 | 371/400 | +83.0% | 8.37e-98 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_provenance` | 40% | benign_utility | benign | 11/100 | 100/100 | +89.0% | 1.01e-24 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_provenance` | 40% | strict_json | all_fullkv_correct | 401/500 | 500/500 | +19.8% | 1.03e-27 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `system_h2o_pin` | 20% | hierarchy_success | conflict | 199/400 | 278/400 | +19.8% | 9.63e-22 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `system_h2o_pin` | 20% | benign_utility | benign | 97/100 | 50/100 | -47.0% | 1.4e-09 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `system_h2o_pin` | 20% | strict_json | all_fullkv_correct | 496/500 | 500/500 | +0.8% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `system_h2o_pin` | 40% | hierarchy_success | conflict | 280/400 | 289/400 | +2.2% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `system_h2o_pin` | 40% | benign_utility | benign | 2/100 | 50/100 | +48.0% | 2.37e-11 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `system_h2o_pin` | 40% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `system_knorm_pin` | 20% | hierarchy_success | conflict | 297/400 | 302/400 | +1.2% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `system_knorm_pin` | 20% | benign_utility | benign | 94/100 | 83/100 | -11.0% | 0.714 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `system_knorm_pin` | 20% | strict_json | all_fullkv_correct | 498/500 | 500/500 | +0.4% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `system_knorm_pin` | 40% | hierarchy_success | conflict | 361/400 | 372/400 | +2.8% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `system_knorm_pin` | 40% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `system_knorm_pin` | 40% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `system_snapkv_pin` | 20% | hierarchy_success | conflict | 400/400 | 400/400 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `system_snapkv_pin` | 20% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `system_snapkv_pin` | 20% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `system_snapkv_pin` | 40% | hierarchy_success | conflict | 400/400 | 400/400 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `system_snapkv_pin` | 40% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_snapkv` | `system_snapkv_pin` | 40% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `system_streaming_pin` | 20% | hierarchy_success | conflict | 0/400 | 315/400 | +78.8% | 1.08e-92 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `system_streaming_pin` | 20% | benign_utility | benign | 15/100 | 50/100 | +35.0% | 6.88e-07 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `system_streaming_pin` | 20% | strict_json | all_fullkv_correct | 202/500 | 500/500 | +59.6% | 1.41e-87 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `system_streaming_pin` | 40% | hierarchy_success | conflict | 39/400 | 349/400 | +77.5% | 3.46e-91 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `system_streaming_pin` | 40% | benign_utility | benign | 11/100 | 50/100 | +39.0% | 9.59e-09 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `system_streaming_pin` | 40% | strict_json | all_fullkv_correct | 401/500 | 500/500 | +19.8% | 1.03e-27 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | hierarchy_success | conflict | 57/100 | 100/100 | +43.0% | 5.93e-11 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | benign_utility | benign | 20/20 | 20/20 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | strict_json | all_fullkv_correct | 119/120 | 120/120 | +0.8% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | hierarchy_success | conflict | 67/100 | 100/100 | +33.0% | 5.77e-08 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | benign_utility | benign | 1/20 | 20/20 | +95.0% | 0.00087 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | strict_json | all_fullkv_correct | 120/120 | 120/120 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | hierarchy_success | conflict | 70/100 | 100/100 | +30.0% | 4.58e-07 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | benign_utility | benign | 20/20 | 20/20 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | strict_json | all_fullkv_correct | 120/120 | 120/120 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | hierarchy_success | conflict | 80/100 | 100/100 | +20.0% | 0.00045 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | benign_utility | benign | 20/20 | 20/20 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | strict_json | all_fullkv_correct | 120/120 | 120/120 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | hierarchy_success | conflict | 0/100 | 98/100 | +98.0% | 2.03e-27 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | benign_utility | benign | 3/20 | 20/20 | +85.0% | 0.00339 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | strict_json | all_fullkv_correct | 50/120 | 119/120 | +57.5% | 1.7e-17 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | hierarchy_success | conflict | 11/100 | 100/100 | +89.0% | 1.01e-24 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | benign_utility | benign | 3/20 | 20/20 | +85.0% | 0.00339 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | strict_json | all_fullkv_correct | 100/120 | 120/120 | +16.7% | 0.00045 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | hierarchy_success | conflict | 52/100 | 100/100 | +48.0% | 1.9e-12 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | benign_utility | benign | 19/20 | 20/20 | +5.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | strict_json | all_fullkv_correct | 120/120 | 120/120 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | hierarchy_success | conflict | 81/100 | 100/100 | +19.0% | 0.00087 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | benign_utility | benign | 1/20 | 20/20 | +95.0% | 0.00087 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | strict_json | all_fullkv_correct | 120/120 | 120/120 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | hierarchy_success | conflict | 93/100 | 100/100 | +7.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | benign_utility | benign | 19/20 | 20/20 | +5.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | strict_json | all_fullkv_correct | 120/120 | 120/120 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | hierarchy_success | conflict | 97/100 | 99/100 | +2.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | benign_utility | benign | 20/20 | 20/20 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | strict_json | all_fullkv_correct | 120/120 | 119/120 | -0.8% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | hierarchy_success | conflict | 0/100 | 100/100 | +100.0% | 5.22e-28 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | benign_utility | benign | 0/20 | 20/20 | +100.0% | 0.00045 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | strict_json | all_fullkv_correct | 50/120 | 120/120 | +58.3% | 4.81e-19 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | hierarchy_success | conflict | 16/100 | 100/100 | +84.0% | 3.02e-23 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | benign_utility | benign | 2/20 | 20/20 | +90.0% | 0.00171 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | strict_json | all_fullkv_correct | 100/120 | 120/120 | +16.7% | 0.00045 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | hierarchy_success | conflict | 41/100 | 100/100 | +59.0% | 9.51e-16 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | benign_utility | benign | 19/20 | 20/20 | +5.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | strict_json | all_fullkv_correct | 119/120 | 120/120 | +0.8% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | hierarchy_success | conflict | 50/100 | 100/100 | +50.0% | 4.83e-13 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | benign_utility | benign | 0/20 | 20/20 | +100.0% | 0.00045 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | strict_json | all_fullkv_correct | 120/120 | 120/120 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | hierarchy_success | conflict | 70/100 | 100/100 | +30.0% | 4.58e-07 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | benign_utility | benign | 18/20 | 20/20 | +10.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | strict_json | all_fullkv_correct | 120/120 | 120/120 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | hierarchy_success | conflict | 88/100 | 100/100 | +12.0% | 0.104 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | benign_utility | benign | 20/20 | 20/20 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | strict_json | all_fullkv_correct | 120/120 | 120/120 | +0.0% | 1 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | hierarchy_success | conflict | 0/100 | 100/100 | +100.0% | 5.22e-28 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | benign_utility | benign | 2/20 | 20/20 | +90.0% | 0.00171 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | strict_json | all_fullkv_correct | 51/120 | 119/120 | +56.7% | 3.32e-17 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | hierarchy_success | conflict | 5/100 | 100/100 | +95.0% | 1.59e-26 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | benign_utility | benign | 0/20 | 20/20 | +100.0% | 0.00045 |
| Qwen/Qwen2.5-7B-Instruct | `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | strict_json | all_fullkv_correct | 100/120 | 120/120 | +16.7% | 0.00045 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_h2o` | `all_control_h2o_pin` | 20% | hierarchy_success | conflict | 318/320 | 320/320 | +0.6% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_h2o` | `all_control_h2o_pin` | 20% | benign_utility | benign | 51/100 | 100/100 | +49.0% | 9.63e-13 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_h2o` | `all_control_h2o_pin` | 20% | strict_json | all_fullkv_correct | 420/420 | 420/420 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_h2o` | `all_control_h2o_pin` | 40% | hierarchy_success | conflict | 400/400 | 400/400 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_h2o` | `all_control_h2o_pin` | 40% | benign_utility | benign | 99/100 | 100/100 | +1.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_h2o` | `all_control_h2o_pin` | 40% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_knorm` | `all_control_knorm_pin` | 20% | hierarchy_success | conflict | 320/320 | 320/320 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_knorm` | `all_control_knorm_pin` | 20% | benign_utility | benign | 55/100 | 100/100 | +45.0% | 1.51e-11 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_knorm` | `all_control_knorm_pin` | 20% | strict_json | all_fullkv_correct | 420/420 | 420/420 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_knorm` | `all_control_knorm_pin` | 40% | hierarchy_success | conflict | 400/400 | 400/400 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_knorm` | `all_control_knorm_pin` | 40% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_knorm` | `all_control_knorm_pin` | 40% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_snapkv` | `all_control_snapkv_pin` | 20% | hierarchy_success | conflict | 320/320 | 320/320 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_snapkv` | `all_control_snapkv_pin` | 20% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_snapkv` | `all_control_snapkv_pin` | 20% | strict_json | all_fullkv_correct | 420/420 | 420/420 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_snapkv` | `all_control_snapkv_pin` | 40% | hierarchy_success | conflict | 400/400 | 400/400 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_snapkv` | `all_control_snapkv_pin` | 40% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_snapkv` | `all_control_snapkv_pin` | 40% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_streaming` | `all_control_streaming_pin` | 20% | hierarchy_success | conflict | 11/320 | 294/320 | +88.4% | 1.16e-79 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_streaming` | `all_control_streaming_pin` | 20% | benign_utility | benign | 12/100 | 100/100 | +88.0% | 1.98e-24 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_streaming` | `all_control_streaming_pin` | 20% | strict_json | all_fullkv_correct | 172/420 | 420/420 | +59.0% | 1.53e-72 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_streaming` | `all_control_streaming_pin` | 40% | hierarchy_success | conflict | 27/400 | 389/400 | +90.5% | 7.15e-105 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_streaming` | `all_control_streaming_pin` | 40% | benign_utility | benign | 14/100 | 100/100 | +86.0% | 7.73e-24 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_streaming` | `all_control_streaming_pin` | 40% | strict_json | all_fullkv_correct | 413/500 | 500/500 | +17.4% | 3.93e-24 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | hierarchy_success | conflict | 398/400 | 400/400 | +0.5% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | benign_utility | benign | 51/100 | 100/100 | +49.0% | 9.63e-13 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | hierarchy_success | conflict | 400/400 | 400/400 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | benign_utility | benign | 99/100 | 100/100 | +1.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | hierarchy_success | conflict | 400/400 | 400/400 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | benign_utility | benign | 55/100 | 100/100 | +45.0% | 1.51e-11 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | hierarchy_success | conflict | 400/400 | 400/400 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_snapkv` | `authority_snapkv_detected_provenance` | 20% | hierarchy_success | conflict | 400/400 | 400/400 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_snapkv` | `authority_snapkv_detected_provenance` | 20% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_snapkv` | `authority_snapkv_detected_provenance` | 20% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_snapkv` | `authority_snapkv_detected_provenance` | 40% | hierarchy_success | conflict | 400/400 | 400/400 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_snapkv` | `authority_snapkv_detected_provenance` | 40% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_snapkv` | `authority_snapkv_detected_provenance` | 40% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | hierarchy_success | conflict | 13/400 | 400/400 | +96.8% | 2.37e-114 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | benign_utility | benign | 12/100 | 100/100 | +88.0% | 1.98e-24 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | strict_json | all_fullkv_correct | 212/500 | 500/500 | +57.6% | 1.42e-84 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | hierarchy_success | conflict | 27/400 | 400/400 | +93.2% | 3.86e-110 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | benign_utility | benign | 14/100 | 100/100 | +86.0% | 7.73e-24 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | strict_json | all_fullkv_correct | 413/500 | 500/500 | +17.4% | 3.93e-24 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_h2o` | `system_h2o_pin` | 20% | hierarchy_success | conflict | 398/400 | 399/400 | +0.2% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_h2o` | `system_h2o_pin` | 20% | benign_utility | benign | 51/100 | 100/100 | +49.0% | 9.63e-13 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_h2o` | `system_h2o_pin` | 20% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_h2o` | `system_h2o_pin` | 40% | hierarchy_success | conflict | 400/400 | 400/400 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_h2o` | `system_h2o_pin` | 40% | benign_utility | benign | 99/100 | 100/100 | +1.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_h2o` | `system_h2o_pin` | 40% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_knorm` | `system_knorm_pin` | 20% | hierarchy_success | conflict | 400/400 | 400/400 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_knorm` | `system_knorm_pin` | 20% | benign_utility | benign | 55/100 | 100/100 | +45.0% | 1.51e-11 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_knorm` | `system_knorm_pin` | 20% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_knorm` | `system_knorm_pin` | 40% | hierarchy_success | conflict | 400/400 | 400/400 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_knorm` | `system_knorm_pin` | 40% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_knorm` | `system_knorm_pin` | 40% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_snapkv` | `system_snapkv_pin` | 20% | hierarchy_success | conflict | 400/400 | 400/400 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_snapkv` | `system_snapkv_pin` | 20% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_snapkv` | `system_snapkv_pin` | 20% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_snapkv` | `system_snapkv_pin` | 40% | hierarchy_success | conflict | 400/400 | 400/400 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_snapkv` | `system_snapkv_pin` | 40% | benign_utility | benign | 100/100 | 100/100 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_snapkv` | `system_snapkv_pin` | 40% | strict_json | all_fullkv_correct | 500/500 | 500/500 | +0.0% | 1 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_streaming` | `system_streaming_pin` | 20% | hierarchy_success | conflict | 13/400 | 279/400 | +66.5% | 3.95e-76 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_streaming` | `system_streaming_pin` | 20% | benign_utility | benign | 12/100 | 50/100 | +38.0% | 6.12e-05 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_streaming` | `system_streaming_pin` | 20% | strict_json | all_fullkv_correct | 212/500 | 500/500 | +57.6% | 1.42e-84 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_streaming` | `system_streaming_pin` | 40% | hierarchy_success | conflict | 27/400 | 276/400 | +62.3% | 3.29e-68 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_streaming` | `system_streaming_pin` | 40% | benign_utility | benign | 14/100 | 50/100 | +36.0% | 1.06e-05 |
| mistralai/Mistral-7B-Instruct-v0.3 | `kvpress_streaming` | `system_streaming_pin` | 40% | strict_json | all_fullkv_correct | 413/500 | 500/500 | +17.4% | 3.93e-24 |

## Pooled descriptive comparisons

Pooled intervals resample prompt IDs as clusters, keeping cross-model replicas together; exact tests above remain model/dataset stratified.

| Base | Comparison | KV keep | Base ARR | Comparison ARR | Relative reduction | Cluster-bootstrap delta 95% CI |
|---|---|---:|---:|---:|---:|---:|
| `kvpress_h2o` | `all_control_h2o_pin` | 20% | 133/1040 | 76/1040 | 42.9% | [-0.073, -0.036] |
| `kvpress_h2o` | `all_control_h2o_pin` | 40% | 126/1200 | 91/1200 | 27.8% | [-0.043, -0.015] |
| `kvpress_h2o` | `authority_h2o_detected` | 20% | 118/400 | 0/400 | 100.0% | [-0.340, -0.250] |
| `kvpress_h2o` | `authority_h2o_detected` | 40% | 120/400 | 0/400 | 100.0% | [-0.345, -0.255] |
| `kvpress_h2o` | `authority_h2o_detected_provenance` | 10% | 32/100 | 0/100 | 100.0% | [-0.410, -0.230] |
| `kvpress_h2o` | `authority_h2o_detected_provenance` | 20% | 276/1600 | 0/1600 | 100.0% | [-0.200, -0.146] |
| `kvpress_h2o` | `authority_h2o_detected_provenance` | 40% | 263/1600 | 0/1600 | 100.0% | [-0.191, -0.138] |
| `kvpress_h2o` | `authority_h2o_detected_provenance` | 60% | 33/100 | 0/100 | 100.0% | [-0.420, -0.240] |
| `kvpress_h2o` | `authority_h2o_pin` | 20% | 118/400 | 52/400 | 55.9% | [-0.205, -0.125] |
| `kvpress_h2o` | `authority_h2o_pin` | 40% | 120/400 | 71/400 | 40.8% | [-0.160, -0.087] |
| `kvpress_h2o` | `authority_h2o_provenance` | 20% | 118/400 | 43/400 | 63.6% | [-0.228, -0.147] |
| `kvpress_h2o` | `authority_h2o_provenance` | 40% | 120/400 | 68/400 | 43.3% | [-0.165, -0.095] |
| `kvpress_h2o` | `system_h2o_pin` | 20% | 133/1200 | 116/1200 | 12.8% | [-0.032, 0.003] |
| `kvpress_h2o` | `system_h2o_pin` | 40% | 126/1200 | 110/1200 | 12.7% | [-0.028, 0.001] |
| `kvpress_knorm` | `all_control_knorm_pin` | 20% | 81/1040 | 214/1040 | -164.2% | [0.103, 0.154] |
| `kvpress_knorm` | `all_control_knorm_pin` | 40% | 42/1200 | 85/1200 | -102.4% | [0.020, 0.052] |
| `kvpress_knorm` | `authority_knorm_detected` | 20% | 80/400 | 0/400 | 100.0% | [-0.240, -0.163] |
| `kvpress_knorm` | `authority_knorm_detected` | 40% | 39/400 | 0/400 | 100.0% | [-0.128, -0.070] |
| `kvpress_knorm` | `authority_knorm_detected_provenance` | 10% | 0/100 | 0/100 | n/a | [0.000, 0.000] |
| `kvpress_knorm` | `authority_knorm_detected_provenance` | 20% | 158/1600 | 0/1600 | 100.0% | [-0.118, -0.080] |
| `kvpress_knorm` | `authority_knorm_detected_provenance` | 40% | 83/1600 | 0/1600 | 100.0% | [-0.066, -0.039] |
| `kvpress_knorm` | `authority_knorm_detected_provenance` | 60% | 0/100 | 0/100 | n/a | [0.000, 0.000] |
| `kvpress_knorm` | `authority_knorm_pin` | 20% | 80/400 | 1/400 | 98.8% | [-0.235, -0.160] |
| `kvpress_knorm` | `authority_knorm_pin` | 40% | 39/400 | 0/400 | 100.0% | [-0.128, -0.070] |
| `kvpress_knorm` | `authority_knorm_provenance` | 20% | 80/400 | 1/400 | 98.8% | [-0.237, -0.160] |
| `kvpress_knorm` | `authority_knorm_provenance` | 40% | 39/400 | 0/400 | 100.0% | [-0.128, -0.070] |
| `kvpress_knorm` | `system_knorm_pin` | 20% | 81/1200 | 39/1200 | 51.9% | [-0.045, -0.025] |
| `kvpress_knorm` | `system_knorm_pin` | 40% | 42/1200 | 28/1200 | 33.3% | [-0.018, -0.005] |
| `kvpress_snapkv` | `all_control_snapkv_pin` | 20% | 6/1040 | 1/1040 | 83.3% | [-0.010, -0.001] |
| `kvpress_snapkv` | `all_control_snapkv_pin` | 40% | 0/1200 | 0/1200 | n/a | [0.000, 0.000] |
| `kvpress_snapkv` | `authority_snapkv_detected` | 20% | 0/400 | 0/400 | n/a | [0.000, 0.000] |
| `kvpress_snapkv` | `authority_snapkv_detected` | 40% | 0/400 | 0/400 | n/a | [0.000, 0.000] |
| `kvpress_snapkv` | `authority_snapkv_detected_provenance` | 20% | 6/1200 | 0/1200 | 100.0% | [-0.009, -0.002] |
| `kvpress_snapkv` | `authority_snapkv_detected_provenance` | 40% | 0/1200 | 0/1200 | n/a | [0.000, 0.000] |
| `kvpress_snapkv` | `authority_snapkv_pin` | 20% | 0/400 | 0/400 | n/a | [0.000, 0.000] |
| `kvpress_snapkv` | `authority_snapkv_pin` | 40% | 0/400 | 0/400 | n/a | [0.000, 0.000] |
| `kvpress_snapkv` | `authority_snapkv_provenance` | 20% | 0/400 | 0/400 | n/a | [0.000, 0.000] |
| `kvpress_snapkv` | `authority_snapkv_provenance` | 40% | 0/400 | 0/400 | n/a | [0.000, 0.000] |
| `kvpress_snapkv` | `system_snapkv_pin` | 20% | 6/1200 | 0/1200 | 100.0% | [-0.009, -0.002] |
| `kvpress_snapkv` | `system_snapkv_pin` | 40% | 0/1200 | 0/1200 | n/a | [0.000, 0.000] |
| `kvpress_streaming` | `all_control_streaming_pin` | 20% | 503/1040 | 294/1040 | 41.6% | [-0.236, -0.166] |
| `kvpress_streaming` | `all_control_streaming_pin` | 40% | 1105/1200 | 138/1200 | 87.5% | [-0.829, -0.782] |
| `kvpress_streaming` | `authority_streaming_detected` | 20% | 200/400 | 0/400 | 100.0% | [-0.547, -0.450] |
| `kvpress_streaming` | `authority_streaming_detected` | 40% | 361/400 | 0/400 | 100.0% | [-0.930, -0.873] |
| `kvpress_streaming` | `authority_streaming_detected_provenance` | 10% | 50/100 | 0/100 | 100.0% | [-0.600, -0.410] |
| `kvpress_streaming` | `authority_streaming_detected_provenance` | 20% | 768/1600 | 0/1600 | 100.0% | [-0.531, -0.428] |
| `kvpress_streaming` | `authority_streaming_detected_provenance` | 40% | 1463/1600 | 0/1600 | 100.0% | [-0.934, -0.893] |
| `kvpress_streaming` | `authority_streaming_detected_provenance` | 60% | 88/100 | 0/100 | 100.0% | [-0.940, -0.810] |
| `kvpress_streaming` | `authority_streaming_pin` | 20% | 200/400 | 0/400 | 100.0% | [-0.547, -0.453] |
| `kvpress_streaming` | `authority_streaming_pin` | 40% | 361/400 | 29/400 | 92.0% | [-0.865, -0.792] |
| `kvpress_streaming` | `authority_streaming_provenance` | 20% | 200/400 | 0/400 | 100.0% | [-0.547, -0.453] |
| `kvpress_streaming` | `authority_streaming_provenance` | 40% | 361/400 | 29/400 | 92.0% | [-0.868, -0.795] |
| `kvpress_streaming` | `system_streaming_pin` | 20% | 568/1200 | 56/1200 | 90.1% | [-0.479, -0.373] |
| `kvpress_streaming` | `system_streaming_pin` | 40% | 1105/1200 | 77/1200 | 93.0% | [-0.880, -0.833] |
