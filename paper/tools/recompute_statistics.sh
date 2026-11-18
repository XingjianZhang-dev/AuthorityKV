#!/usr/bin/env bash
# Recompute, from the raw predictions, every statistics file that the appendix tables are built from,
# and compare the result with the copy stored under reports/.
#
#   bash paper/tools/recompute_statistics.sh            # recompute into a temporary directory and compare
#   bash paper/tools/recompute_statistics.sh OUT_DIR    # keep the recomputed files in OUT_DIR
#
# Run from the repository root after extracting raw_outputs/ (see README). CPU only, about ten minutes.
# The System-IFEval step uses the official grader (its packages are in requirements-cpu.txt) and NLTK punkt_tab.
set -u -o pipefail

OUT="${1:-$(mktemp -d)}"
PY="${PYTHON:-python}"
R=results/authoritykv
status=0

compare_dir() {   # compare_dir <recomputed dir> <stored dir>
    local f b
    for f in "$1"/*; do
        b="$(basename "$f")"
        if cmp -s "$f" "$2/$b"; then
            printf '  identical  %s/%s\n' "$2" "$b"
        else
            printf '  DIFFERENT  %s/%s\n' "$2" "$b"; status=1
        fi
    done
}
compare_file() {  # compare_file <recomputed file> <stored file>
    if cmp -s "$1" "$2"; then printf '  identical  %s\n' "$2"; else printf '  DIFFERENT  %s\n' "$2"; status=1; fi
}

# ---- IH-CacheBench, three models: reversal, hierarchy and benign counts, exact McNemar tests, bootstrap intervals
P=aclmain_20260725v1
RUNS="${P}_qwen7b_fullkv500,${P}_mistral7b_fullkv500,${P}_yi9b_fullkv500,${P}_qwen7b_official_nonh2o500"
RUNS+=",${P}_qwen7b_snapkv_compositions500,${P}_qwen7b_streaming_compositions500,${P}_qwen7b_knorm_compositions500,${P}_qwen7b_h2o_compositions500"
for m in mistral7b yi9b; do
    RUNS+=",${P}_${m}_official_nonh2o500,${P}_${m}_core_compositions500,${P}_${m}_core_h2o500"
done
RUNS+=",${P}_qwen7b_curve_nonh2o120,${P}_qwen7b_curve_h2o120"
for h in heldout_paraphrase heldout_display heldout_option; do
    RUNS+=",${P}_qwen7b_${h}_fullkv120,${P}_qwen7b_${h}_nonh2o120,${P}_qwen7b_${h}_h2o120"
done
echo "[1/8] main matrix"
"$PY" scripts/summarize_acl_main_runs.py --run-prefix "$RUNS" --out-dir "$OUT/parent_statistics" \
    --protocol-amendment configs/acl_main_decode_cap_amendment.json \
    --allowed-source-sha256 5722fc56056eb4d4b5bedb4b88481465f7e230cfe97946663663ec50f8fbba18 \
    --allowed-source-sha256 c561287ca070c581bdae2b32f6494efb15321c18392fcd292716e0b4831e252e \
    --allowed-source-sha256 7fc39622f006a6ab15bf933e1723b8b50fbebde3741f6ba45dfce5eca941160b \
    --allowed-source-sha256 35b24cb35724341f36dfe1e0d666fa2a866b8e0f538ac83ecb411a6f7002dfa3 \
    --bootstrap-samples 5000 > /dev/null || status=1
compare_dir "$OUT/parent_statistics" reports/acl_final_closure/parent_statistics

F=aclfollow_20260725v2
echo "[2/8] position-balanced replication"
"$PY" scripts/summarize_acl_main_runs.py \
    --run-prefix "${F}_qwen7b_noprefix_fullkv120,${F}_qwen7b_noprefix_nonh2o120,${F}_qwen7b_noprefix_h2o120" \
    --out-dir "$OUT/no_prefix_statistics" --bootstrap-samples 5000 > /dev/null || status=1
compare_dir "$OUT/no_prefix_statistics" reports/acl_final_closure/no_prefix_statistics

echo "[3/8] conflict-free LongBench and RULER utility"
"$PY" scripts/summarize_external_utility_runs.py --run-prefix "${P}_qwen7b_utility_" --out-dir "$OUT/parent_utility" \
    --allowed-source-sha256 b79f92cabcb0bda3a84090798ec703a91c4e1d6abf0a682070c1793333f5dd75 \
    --allowed-source-sha256 5cd8312c33e81eea04ea4d5d19104ace9f5776d0de6f9056ea067641f6a312c9 \
    --bootstrap-samples 5000 > /dev/null || status=1
compare_dir "$OUT/parent_utility" reports/acl_final_closure/parent_utility

echo "[4/8] IH-Challenge"
for m in qwen7b mistral7b yi9b; do
    "$PY" scripts/summarize_ih_challenge_runs.py --run-prefix "${F}_${m}_ih_" --out-dir "$OUT/ih_${m}" \
        --bootstrap-samples 5000 > /dev/null || status=1
    compare_dir "$OUT/ih_${m}" "reports/acl_final_closure/ih_${m}"
done

echo "[5/8] prefill time and memory"
"$PY" scripts/summarize_systems_benchmark.py --run-prefix "${F}_qwen7b_systems_" --out-dir "$OUT/systems" > /dev/null || status=1
compare_dir "$OUT/systems" reports/aclfollow_20260725v2_randomized_systems

echo "[6/8] matched 8k intervention"
"$PY" scripts/summarize_matched_causal_followup.py --config configs/acl_main_matched_causal_followup.json \
    --run-dir "$R/akvcausal_20260726v4_matched_long8k30" --prior-run "$R/akvopt_20260725v3_long8k_extreme_adaptive30" \
    --out-dir "$OUT/matched" > /dev/null || status=1
compare_dir "$OUT/matched" reports/akvcausal_20260726v4_matched

echo "[7/8] System-IFEval and LongBench with an injected instruction (official grader, stored predictions)"
E=reports/arr_august_external_closure/full
mkdir -p "$OUT/standard_tasks"
"$PY" scripts/score_system_ifeval.py --predictions "$R/arrsys_20260726v2_qwen_fullkv_full150/predictions.jsonl" \
    "$R/arrsys_20260726v4_qwen_streaming40_full150/predictions.jsonl" "$R/arrsys_20260726v4_qwen_knorm40_full150/predictions.jsonl" \
    --out "$OUT/standard_tasks/system_ifeval_full_v4_metrics.json" \
    --judgments-out "$OUT/standard_tasks/system_ifeval_full_v4_judgments.jsonl" > /dev/null || status=1
for s in streaming knorm40; do
    "$PY" scripts/score_mixed_evidence_attack.py --predictions "$R/arrmixed_20260726v1_qwen_fullkv_full300/predictions.jsonl" \
        "$R/arrmixed_20260726v4_qwen_${s}_full300/predictions.jsonl" \
        --out "$OUT/standard_tasks/mixed_evidence_${s}_full_v4_metrics.json" \
        --judgments-out "$OUT/standard_tasks/mixed_evidence_${s}_full_v4_judgments.jsonl" > /dev/null || status=1
done
compare_dir "$OUT/standard_tasks" "$E"

echo "[8/8] retained-token counts of base and AuthorityKV on the same example and budget"
PAIRS=()
while IFS= read -r spec; do PAIRS+=(--pair "$spec"); done < <("$PY" - <<'EOF'
import json
for p in json.load(open("reports/acl_final_closure/paired_budget_equivalence.json"))["pairs"]:
    print("|".join(str(p[k]) for k in ("name", "base_run", "base_method", "comparison_run", "comparison_method", "expected_pairs")))
EOF
)
"$PY" scripts/audit_paired_budget_equivalence.py --results-root "$R" "${PAIRS[@]}" --out "$OUT/paired_budget_equivalence.json" > /dev/null || status=1
if "$PY" - "$OUT/paired_budget_equivalence.json" reports/acl_final_closure/paired_budget_equivalence.json <<'EOF'
import json, sys
a, b = (json.load(open(p)) for p in sys.argv[1:3])
a.pop("audited_at_utc", None); b.pop("audited_at_utc", None)   # the only field that depends on when the audit ran
sys.exit(0 if a == b else 1)
EOF
then echo "  identical  reports/acl_final_closure/paired_budget_equivalence.json (apart from the audit timestamp)"
else echo "  DIFFERENT  reports/acl_final_closure/paired_budget_equivalence.json"; status=1; fi

if [ "$status" -eq 0 ]; then echo "All recomputed statistics match the stored files. Recomputed copies: $OUT"
else echo "Some files differ or a step failed; see above. Recomputed copies: $OUT"; fi
exit "$status"
