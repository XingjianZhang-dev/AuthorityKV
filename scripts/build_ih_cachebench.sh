#!/usr/bin/env bash
# Regenerate every IH-CacheBench file from its seed and compare it with the released copy.
#   bash scripts/build_ih_cachebench.sh            # build into a temporary directory and compare
#   bash scripts/build_ih_cachebench.sh OUT_DIR    # keep the regenerated files in OUT_DIR
# Run from the repository root. CPU only, a few seconds.
set -eu -o pipefail
OUT="${1:-$(mktemp -d)}"
PY="${PYTHON:-python}"
D=data/ih_cachebench
mkdir -p "$OUT"

build() {  # build <file> <conflicts per relation> <benign> <prompt tokens> <conflict style> <seed> [extra args]
    local name="$1"; shift
    "$PY" scripts/make_ih_cachebench.py --out "$OUT/$name" --conflict-per-category "$1" --benign "$2" \
        --target-prompt-tokens "$3" --format-style natural --conflict-style "$4" --seed "$5" "${@:6}" > /dev/null
}
build natural_short_500.jsonl                       80 100 2048 default               20260530   # primary split
build natural_short_120.jsonl                       20  20 2048 default               20260530   # replication and budget curve
build natural_short_heldout_paraphrase_120.jsonl    20  20 2048 heldout_paraphrase    20260725   # held-out surfaces
build natural_short_heldout_display_label_120.jsonl 20  20 2048 heldout_display_label 20260726
build natural_short_heldout_option_card_120.jsonl   20  20 2048 heldout_option_card   20260727
build outcome_informed_long_8k_30.jsonl              5   5 6144 default               20260725 --id-prefix outcome8k_   # matched 8k set
"$PY" scripts/make_stratified_subset.py --input "$OUT/natural_short_500.jsonl" \
    --output "$OUT/natural_short_stratified_30.jsonl" --per-category 5 --seed 20260725 > /dev/null   # systems measurements

status=0
for f in "$OUT"/*.jsonl; do
    if cmp -s "$f" "$D/$(basename "$f")"; then echo "identical  $D/$(basename "$f")"
    else echo "DIFFERENT  $D/$(basename "$f")"; status=1; fi
done
exit "$status"
