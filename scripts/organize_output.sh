#!/usr/bin/env bash
#
# Organize output from Mixtapes pipeline:
#   1. Find all promptXX directories
#   2. Rename concatenated files by appending __<sanitized_prompt>
#   3. Move renamed files to a single output directory
#   4. Delete noise_level-* subdirectories
#
# Usage:
#   bash scripts/organize_output.sh /path/to/output_dir
#

set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <directory>" >&2
    exit 1
fi

BASE_DIR="$1"
OUTPUT_DIR="${BASE_DIR}/final_output"

mkdir -p "$OUTPUT_DIR"

echo "==== Organizing output in: $BASE_DIR ===="
echo ""

# Find all promptXX directories
for prompt_dir in "$BASE_DIR"/prompt[0-9][0-9]_*; do
    [[ -d "$prompt_dir" ]] || continue

    prompt_name=$(basename "$prompt_dir")
    echo "---- $prompt_name ----"

    # Check for params.json and concatenated/
    if [[ ! -f "$prompt_dir/params.json" ]]; then
        echo "  WARNING: no params.json, skipping"
        continue
    fi
    if [[ ! -d "$prompt_dir/concatenated" ]]; then
        echo "  WARNING: no concatenated/ dir, skipping"
        continue
    fi

    # Extract prompt number (e.g., "01" from "prompt01_sweep...")
    prompt_num=$(basename "$prompt_dir" | sed -n 's/^prompt\([0-9][0-9]\)_.*/\1/p')

    # Read prompt from params.json and sanitize
    raw_prompt=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['prompt'])" "$prompt_dir/params.json")
    safe_prompt=$(echo "$raw_prompt" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-')
    echo "  prompt: $raw_prompt"
    echo "  sanitized: $safe_prompt"

    # Rename and move concatenated files
    for wav in "$prompt_dir/concatenated"/*.wav; do
        [[ -f "$wav" ]] || continue
        base=$(basename "$wav" .wav)
        new_name="${prompt_num}_${base}__${safe_prompt}.wav"
        mv "$wav" "$OUTPUT_DIR/$new_name"
        echo "  -> $new_name"
    done

    # Delete noise_level-* subdirectories
    for nl_dir in "$prompt_dir"/noise_level-*; do
        [[ -d "$nl_dir" ]] || continue
        rm -rf "$nl_dir"
        echo "  deleted $(basename "$nl_dir")"
    done

    echo ""
done

echo "==== Done — files moved to: $OUTPUT_DIR ===="
