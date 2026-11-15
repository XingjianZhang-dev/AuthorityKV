#!/usr/bin/env bash
# Supervisor-friendly ACL Main sweep: primary, robustness, and utility evidence.

set -u -o pipefail

PROJECT_ROOT="${AUTHORITYKV_PROJECT_ROOT:-/workspace/authoritykv}"
VENV_ROOT="${AUTHORITYKV_VENV_ROOT:-/venv/main}"
RUN_LABEL="${AUTHORITYKV_RUN_LABEL:-20260725v1}"
DATASET="data/ih_cachebench/natural_short_500.jsonl"
CURVE_DATASET="data/ih_cachebench/natural_short_120.jsonl"
ASSISTANT_PREFIX='{"decision":"'
PARENT_CONFIG="configs/acl_main_experiment_matrix.json"
DECODE_CAP_AMENDMENT="configs/acl_main_decode_cap_amendment.json"

cd "$PROJECT_ROOT" || exit 2
source "$VENV_ROOT/bin/activate" || exit 2
mkdir -p logs results/authoritykv

generation_complete() {
    local out_dir="$1"
    test -s "$out_dir/predictions.jsonl" \
        && test -s "$out_dir/run_config.json" \
        && grep -q '"end_time"' "$out_dir/run_config.json"
}

generation_exit_success() {
    local out_dir="$1"
    local marker="$out_dir/runner_exit_code.txt"
    if ! test -s "$marker"; then
        printf 'Missing generation exit metadata: %s\n' "$marker" >&2
        return 22
    fi
    local status
    status="$(tr -d '[:space:]' < "$marker")"
    if ! [[ "$status" =~ ^[0-9]+$ ]]; then
        printf 'Invalid generation exit metadata: %s\n' "$marker" >&2
        return 22
    fi
    if test "$status" -ne 0; then
        printf 'Generation previously failed: %s (exit=%s)\n' \
            "$out_dir" "$status" >&2
        return "$status"
    fi
}

is_complete() {
    local out_dir="$1"
    generation_complete "$out_dir" \
        && generation_exit_success "$out_dir" \
        && test -s "$out_dir/metrics.json" \
        && test "$(tr -d '[:space:]' < "$out_dir/judge_exit_code.txt" 2>/dev/null)" = "0"
}

require_success() {
    local stage="$1"
    shift
    "$@"
    local stage_status="$?"
    if test "$stage_status" -ne 0; then
        printf 'Required parent stage failed: %s (exit=%s)\n' \
            "$stage" "$stage_status" >&2
        exit 20
    fi
}

run_fullkv() {
    local tag="$1"
    local model="$2"
    local run_id="aclmain_${RUN_LABEL}_${tag}_fullkv500"
    local out_dir="results/authoritykv/$run_id"
    local log_path="logs/${run_id}.log"

    if is_complete "$out_dir"; then
        return 0
    fi
    if ! generation_complete "$out_dir"; then
        mkdir -p "$out_dir"
        python scripts/run_kvpress_authority.py \
            --run-id "$run_id" \
            --model "$model" \
            --dataset "$DATASET" \
            --methods fullkv \
            --max-new-tokens 16 \
            --dtype bf16 \
            --assistant-prefix "$ASSISTANT_PREFIX" \
            --stop-after-json-object \
            --out-dir "$out_dir" 2>&1 | tee "$log_path"
        local run_status="${PIPESTATUS[0]}"
        printf '%s\n' "$run_status" > "$out_dir/runner_exit_code.txt"
        if test "$run_status" -ne 0; then
            return "$run_status"
        fi
    fi
    generation_exit_success "$out_dir" || return $?
    python scripts/judge_authoritykv.py --run-dir "$out_dir" 2>&1 \
        | tee -a "$log_path"
    local judge_status="${PIPESTATUS[0]}"
    printf '%s\n' "$judge_status" > "$out_dir/judge_exit_code.txt"
    return "$judge_status"
}

run_group() {
    local tag="$1"
    local model="$2"
    local group="$3"
    local methods="$4"
    local keep_ratios="$5"
    local dataset="${6:-$DATASET}"
    local fullkv_run="results/authoritykv/aclmain_${RUN_LABEL}_${tag}_fullkv500"
    local dataset_tag="500"
    if test "$dataset" = "$CURVE_DATASET"; then
        dataset_tag="120"
    fi
    local run_id="aclmain_${RUN_LABEL}_${tag}_${group}${dataset_tag}"
    local out_dir="results/authoritykv/$run_id"
    local log_path="logs/${run_id}.log"
    local max_new_tokens=16
    local experiment_config="$PARENT_CONFIG"
    if test "$tag" = "mistral7b" || test "$tag" = "yi9b"; then
        max_new_tokens=32
        experiment_config="$DECODE_CAP_AMENDMENT"
    fi

    if is_complete "$out_dir"; then
        return 0
    fi
    if ! generation_complete "$out_dir"; then
        mkdir -p "$out_dir"
        python scripts/run_kvpress_authority.py \
            --run-id "$run_id" \
            --model "$model" \
            --dataset "$dataset" \
            --methods "$methods" \
            --keep-ratios "$keep_ratios" \
            --max-new-tokens "$max_new_tokens" \
            --dtype bf16 \
            --experiment-config "$experiment_config" \
            --assistant-prefix "$ASSISTANT_PREFIX" \
            --stop-after-json-object \
            --out-dir "$out_dir" 2>&1 | tee "$log_path"
        local run_status="${PIPESTATUS[0]}"
        printf '%s\n' "$run_status" > "$out_dir/runner_exit_code.txt"
        if test "$run_status" -ne 0; then
            return "$run_status"
        fi
    fi
    generation_exit_success "$out_dir" || return $?
    python scripts/judge_authoritykv.py \
        --run-dir "$out_dir" \
        --fullkv-run "$fullkv_run" 2>&1 | tee -a "$log_path"
    local judge_status="${PIPESTATUS[0]}"
    printf '%s\n' "$judge_status" > "$out_dir/judge_exit_code.txt"
    return "$judge_status"
}

run_heldout_fullkv() {
    local tag="$1"
    local dataset="$2"
    local run_id="aclmain_${RUN_LABEL}_qwen7b_${tag}_fullkv120"
    local out_dir="results/authoritykv/$run_id"
    local log_path="logs/${run_id}.log"

    if is_complete "$out_dir"; then
        return 0
    fi
    if ! generation_complete "$out_dir"; then
        mkdir -p "$out_dir"
        python scripts/run_kvpress_authority.py \
            --run-id "$run_id" \
            --model "$QWEN_MODEL" \
            --dataset "$dataset" \
            --methods fullkv \
            --max-new-tokens 16 \
            --dtype bf16 \
            --assistant-prefix "$ASSISTANT_PREFIX" \
            --stop-after-json-object \
            --out-dir "$out_dir" 2>&1 | tee "$log_path"
        local run_status="${PIPESTATUS[0]}"
        printf '%s\n' "$run_status" > "$out_dir/runner_exit_code.txt"
        if test "$run_status" -ne 0; then
            return "$run_status"
        fi
    fi
    generation_exit_success "$out_dir" || return $?
    python scripts/judge_authoritykv.py --run-dir "$out_dir" 2>&1 \
        | tee -a "$log_path"
    local judge_status="${PIPESTATUS[0]}"
    printf '%s\n' "$judge_status" > "$out_dir/judge_exit_code.txt"
    return "$judge_status"
}

run_heldout_group() {
    local tag="$1"
    local group="$2"
    local methods="$3"
    local dataset="$4"
    local fullkv_run="results/authoritykv/aclmain_${RUN_LABEL}_qwen7b_${tag}_fullkv120"
    local run_id="aclmain_${RUN_LABEL}_qwen7b_${tag}_${group}120"
    local out_dir="results/authoritykv/$run_id"
    local log_path="logs/${run_id}.log"

    if is_complete "$out_dir"; then
        return 0
    fi
    if ! generation_complete "$out_dir"; then
        mkdir -p "$out_dir"
        python scripts/run_kvpress_authority.py \
            --run-id "$run_id" \
            --model "$QWEN_MODEL" \
            --dataset "$dataset" \
            --methods "$methods" \
            --keep-ratios "0.2,0.4" \
            --max-new-tokens 16 \
            --dtype bf16 \
            --assistant-prefix "$ASSISTANT_PREFIX" \
            --stop-after-json-object \
            --out-dir "$out_dir" 2>&1 | tee "$log_path"
        local run_status="${PIPESTATUS[0]}"
        printf '%s\n' "$run_status" > "$out_dir/runner_exit_code.txt"
        if test "$run_status" -ne 0; then
            return "$run_status"
        fi
    fi
    generation_exit_success "$out_dir" || return $?
    python scripts/judge_authoritykv.py \
        --run-dir "$out_dir" \
        --fullkv-run "$fullkv_run" 2>&1 | tee -a "$log_path"
    local judge_status="${PIPESTATUS[0]}"
    printf '%s\n' "$judge_status" > "$out_dir/judge_exit_code.txt"
    return "$judge_status"
}

heldout_gate_passes() {
    local metrics_path="$1"
    python - "$metrics_path" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as handle:
        row = json.load(handle)["by_method"]["fullkv@1.00"]
except (OSError, KeyError, TypeError, ValueError):
    raise SystemExit(1)
passed = (
    row.get("hierarchy_success") is not None
    and float(row["hierarchy_success"]) >= 0.8
    and row.get("benign_utility") is not None
    and float(row["benign_utility"]) >= 0.8
    and row.get("malformed_rate") is not None
    and float(row["malformed_rate"]) <= 0.05
    and int(row.get("errors", 0)) == 0
)
raise SystemExit(0 if passed else 1)
PY
}

run_heldout_suite() {
    local tag="$1"
    local dataset="$2"
    local fullkv_id="aclmain_${RUN_LABEL}_qwen7b_${tag}_fullkv120"
    local fullkv_dir="results/authoritykv/$fullkv_id"

    require_success "${tag}_fullkv" \
        run_heldout_fullkv "$tag" "$dataset"
    if ! heldout_gate_passes "$fullkv_dir/metrics.json"; then
        printf '%s\n' \
            "Held-out FullKV gate failed: hierarchy/benign/format validity" \
            > "$fullkv_dir/COMPRESSION_SKIPPED_GATE_FAILED.txt"
        return 0
    fi
    require_success "${tag}_nonh2o" \
        run_heldout_group "$tag" nonh2o "$HELDOUT_NON_H2O" "$dataset"
    require_success "${tag}_h2o" \
        run_heldout_group "$tag" h2o "$HELDOUT_H2O" "$dataset"
}

utility_complete() {
    local out_dir="$1"
    generation_complete "$out_dir" \
        && generation_exit_success "$out_dir" \
        && test -s "$out_dir/metrics.json"
}

run_utility_group() {
    local tag="$1"
    local group="$2"
    local dataset="$3"
    local methods="$4"
    local max_new_tokens="$5"
    local run_id="aclmain_${RUN_LABEL}_qwen7b_utility_${tag}_${group}"
    local out_dir="results/authoritykv/$run_id"
    local log_path="logs/${run_id}.log"

    if utility_complete "$out_dir"; then
        return 0
    fi
    mkdir -p "$out_dir"
    python scripts/run_kvpress_external_utility.py \
        --run-id "$run_id" \
        --model "$QWEN_MODEL" \
        --dataset "$dataset" \
        --methods "$methods" \
        --keep-ratios "0.2,0.4" \
        --max-new-tokens "$max_new_tokens" \
        --dtype bf16 \
        --use-chat-template \
        --out-dir "$out_dir" 2>&1 | tee "$log_path"
    local run_status="${PIPESTATUS[0]}"
    printf '%s\n' "$run_status" > "$out_dir/runner_exit_code.txt"
    return "$run_status"
}

utility_gate_passes() {
    local metrics_path="$1"
    local metric_field="$2"
    local threshold="$3"
    python - "$metrics_path" "$metric_field" "$threshold" <<'PY'
import json
import sys

path, field, threshold = sys.argv[1], sys.argv[2], float(sys.argv[3])
with open(path, encoding="utf-8") as handle:
    metrics = json.load(handle)
row = metrics.get("by_method", {}).get("fullkv@1.00", {})
value = row.get(field)
errors = metrics.get("errors")
raise SystemExit(0 if value is not None and float(value) >= threshold and errors == 0 else 1)
PY
}

run_utility_suite() {
    local tag="$1"
    local dataset="$2"
    local metric_field="$3"
    local threshold="$4"
    local max_new_tokens="$5"
    local fullkv_id="aclmain_${RUN_LABEL}_qwen7b_utility_${tag}_fullkv"
    local fullkv_dir="results/authoritykv/$fullkv_id"

    require_success "utility_${tag}_fullkv" \
        run_utility_group "$tag" fullkv "$dataset" fullkv "$max_new_tokens"
    if ! utility_gate_passes "$fullkv_dir/metrics.json" "$metric_field" "$threshold"; then
        printf '%s\n' "FullKV gate failed: ${metric_field}<${threshold}" \
            > "$fullkv_dir/COMPRESSION_SKIPPED_GATE_FAILED.txt"
        return 0
    fi
    require_success "utility_${tag}_nonh2o" \
        run_utility_group "$tag" nonh2o "$dataset" \
        "kvpress_streaming,authority_streaming_detected_provenance,kvpress_knorm,authority_knorm_detected_provenance" \
        "$max_new_tokens"
    require_success "utility_${tag}_h2o" \
        run_utility_group "$tag" h2o "$dataset" \
        "kvpress_h2o,authority_h2o_detected_provenance" \
        "$max_new_tokens"
}

QWEN_MODEL="Qwen/Qwen2.5-7B-Instruct"
MISTRAL_MODEL="mistralai/Mistral-7B-Instruct-v0.3"
YI_MODEL="01-ai/Yi-1.5-9B-Chat"

OFFICIAL_NON_H2O="kvpress_snapkv,kvpress_streaming,kvpress_tova,kvpress_knorm,kvpress_pyramid"
SNAPKV_COMPOSITIONS="system_snapkv_pin,all_control_snapkv_pin,authority_snapkv_pin,authority_snapkv_detected,authority_snapkv_provenance,authority_snapkv_detected_provenance"
STREAMING_COMPOSITIONS="system_streaming_pin,all_control_streaming_pin,authority_streaming_pin,authority_streaming_detected,authority_streaming_provenance,authority_streaming_detected_provenance"
KNORM_COMPOSITIONS="system_knorm_pin,all_control_knorm_pin,authority_knorm_pin,authority_knorm_detected,authority_knorm_provenance,authority_knorm_detected_provenance"
H2O_COMPOSITIONS="kvpress_h2o,system_h2o_pin,all_control_h2o_pin,authority_h2o_pin,authority_h2o_detected,authority_h2o_provenance,authority_h2o_detected_provenance"
CORE_COMPOSITIONS="system_snapkv_pin,all_control_snapkv_pin,authority_snapkv_detected_provenance,system_streaming_pin,all_control_streaming_pin,authority_streaming_detected_provenance,system_knorm_pin,all_control_knorm_pin,authority_knorm_detected_provenance"
CORE_H2O="kvpress_h2o,system_h2o_pin,all_control_h2o_pin,authority_h2o_detected_provenance"

require_success qwen7b_fullkv run_fullkv qwen7b "$QWEN_MODEL"
require_success mistral7b_fullkv run_fullkv mistral7b "$MISTRAL_MODEL"
require_success yi9b_fullkv run_fullkv yi9b "$YI_MODEL"

require_success qwen7b_official_nonh2o run_group qwen7b "$QWEN_MODEL" official_nonh2o "$OFFICIAL_NON_H2O" "0.2,0.4"
require_success qwen7b_snapkv_compositions run_group qwen7b "$QWEN_MODEL" snapkv_compositions "$SNAPKV_COMPOSITIONS" "0.2,0.4"
require_success qwen7b_streaming_compositions run_group qwen7b "$QWEN_MODEL" streaming_compositions "$STREAMING_COMPOSITIONS" "0.2,0.4"
require_success qwen7b_knorm_compositions run_group qwen7b "$QWEN_MODEL" knorm_compositions "$KNORM_COMPOSITIONS" "0.2,0.4"
require_success qwen7b_h2o_compositions run_group qwen7b "$QWEN_MODEL" h2o_compositions "$H2O_COMPOSITIONS" "0.2,0.4"

require_success mistral7b_official_nonh2o run_group mistral7b "$MISTRAL_MODEL" official_nonh2o "$OFFICIAL_NON_H2O" "0.2,0.4"
require_success mistral7b_core_compositions run_group mistral7b "$MISTRAL_MODEL" core_compositions "$CORE_COMPOSITIONS" "0.2,0.4"
require_success mistral7b_core_h2o run_group mistral7b "$MISTRAL_MODEL" core_h2o "$CORE_H2O" "0.2,0.4"

require_success yi9b_official_nonh2o run_group yi9b "$YI_MODEL" official_nonh2o "$OFFICIAL_NON_H2O" "0.2,0.4"
require_success yi9b_core_compositions run_group yi9b "$YI_MODEL" core_compositions "$CORE_COMPOSITIONS" "0.2,0.4"
require_success yi9b_core_h2o run_group yi9b "$YI_MODEL" core_h2o "$CORE_H2O" "0.2,0.4"

require_success qwen7b_curve_nonh2o run_group qwen7b "$QWEN_MODEL" curve_nonh2o \
    "kvpress_streaming,authority_streaming_detected_provenance,kvpress_knorm,authority_knorm_detected_provenance" \
    "0.1,0.2,0.4,0.6" "$CURVE_DATASET"
require_success qwen7b_curve_h2o run_group qwen7b "$QWEN_MODEL" curve_h2o \
    "kvpress_h2o,authority_h2o_detected_provenance" \
    "0.1,0.2,0.4,0.6" "$CURVE_DATASET"

HELDOUT_NON_H2O="kvpress_streaming,authority_streaming_detected_provenance,kvpress_knorm,authority_knorm_detected_provenance"
HELDOUT_H2O="kvpress_h2o,authority_h2o_detected_provenance"

run_heldout_suite heldout_paraphrase \
    "data/ih_cachebench/natural_short_heldout_paraphrase_120.jsonl"

run_heldout_suite heldout_display \
    "data/ih_cachebench/natural_short_heldout_display_label_120.jsonl"

run_heldout_suite heldout_option \
    "data/ih_cachebench/natural_short_heldout_option_card_120.jsonl"

run_utility_suite triviaqa \
    "data/external_utility/longbench_official_triviaqa_50.jsonl" \
    longbench_score 0.50 64
run_utility_suite 2wikimqa \
    "data/external_utility/longbench_official_2wikimqa_50.jsonl" \
    longbench_score 0.25 64
run_utility_suite ruler4k \
    "data/external_utility/ruler_official_qwen25_4k_24.jsonl" \
    utility_accuracy 0.80 32

printf '%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    > "results/authoritykv/aclmain_${RUN_LABEL}_QUEUE_FINISHED.txt"
