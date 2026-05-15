
#!/usr/bin/env bash
#
# music51_01.sh
#
# Pipeline:
#   0. Clear OUTPUT_DIR (fresh run; skip with SKIP_CLEAR_OUTPUT_DIR=1)
#   1. Segment a WAV into equal-length clips (python/segment_audio.py)
#   2-4. For each prompt in the prompt JSON file:
#        2. Run interpolateGen.py (init_noise_level sweep) on the segments
#        3. Organize outputs by noise level and concatenate (workflow_noise_level_concat.py)
#        4. Move this run’s concatenated/ WAVs up to OUTPUT_DIR (bringConcatenationsToParent.py)
#
# Usage:
#   bash scripts/music51_01.sh

set -euo pipefail

PROJ_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJ_ROOT"

# --- Paths ---
# Step 1: set AUDIO_FILE to the source WAV. If SEGMENTS_DIR already has clips from a prior run,
# skip step 1: SKIP_SEGMENT_STEP=1 bash scripts/music51_01.sh
# Step 0 clears OUTPUT_DIR; to keep prior outputs: SKIP_CLEAR_OUTPUT_DIR=1 bash scripts/music51_01.sh
SKIP_SEGMENT_STEP="${SKIP_SEGMENT_STEP:-0}"
SKIP_CLEAR_OUTPUT_DIR="${SKIP_CLEAR_OUTPUT_DIR:-0}"
AUDIO_FILE="/Users/brandonwoosnyder/Dropbox/docs-d/06_Live_Laptop/Live Max Instrument/LiveLaptopInstrument2/data/saoLink/buff8.wav"
SEGMENT_MAX_SECONDS="${SEGMENT_MAX_SECONDS:-11}"  # passed to segment_audio.py --max-seconds
# Step 1 writes segment WAVs here; steps 2–3 read this folder as --init-audio (unless MAX_SEGMENTS uses a temp dir).
SEGMENTS_DIR="/Users/brandonwoosnyder/Dropbox/docs-d/06_Live_Laptop/Live Max Instrument/LiveLaptopInstrument2/data/saoLink/Segments"
# Parent directory for each prompt’s sweep (interpolateGen + workflow). Not used unless referenced below.
OUTPUT_DIR="/Users/brandonwoosnyder/Dropbox/docs-d/06_Live_Laptop/Live Max Instrument/LiveLaptopInstrument2/data/saoOutfiles"
PROMPT_FILE="scripts/music51_01_prompts.json"
MAX_SEGMENTS=""  # leave empty for all segments, or set e.g. "5" for quick iteration
SWEEP_N=2  # init_noise_level samples; must match --noise-levels in step 3
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"


# ============================================================
# STEP 0 — Clear OUTPUT_DIR (start fresh)
# ============================================================
if [[ "$SKIP_CLEAR_OUTPUT_DIR" == "1" ]]; then
    echo "==== STEP 0: skipped (SKIP_CLEAR_OUTPUT_DIR=1) ===="
    echo "  leaving OUTPUT_DIR as-is: $OUTPUT_DIR"
    echo ""
elif [[ -z "${OUTPUT_DIR:-}" || "$OUTPUT_DIR" == "/" ]]; then
    echo "OUTPUT_DIR is empty or '/' — refusing to clear." >&2
    exit 1
else
    echo "==== STEP 0: Clearing OUTPUT_DIR ===="
    echo "  $OUTPUT_DIR"
    echo ""
    mkdir -p "$OUTPUT_DIR"
    # Remove everything inside OUTPUT_DIR (depth-first); keeps the directory itself.
    find "$OUTPUT_DIR" -mindepth 1 -delete
    echo "  done."
    echo ""
fi


# ============================================================
# STEP 1 — Segment WAV into clips (runs once)
# ============================================================
if [[ "$SKIP_SEGMENT_STEP" == "1" ]]; then
    echo "==== STEP 1: skipped (SKIP_SEGMENT_STEP=1) ===="
    echo "  using existing segments in: $SEGMENTS_DIR"
    echo ""
elif [[ -z "${AUDIO_FILE:-}" ]]; then
    echo "AUDIO_FILE is unset. Uncomment/set it under \"--- Paths ---\","
    echo "or skip segmentation when SEGMENTS_DIR already has clips: SKIP_SEGMENT_STEP=1" >&2
    exit 1
else
    echo "==== STEP 1: segment_audio.py ===="
    echo "  audio:        $AUDIO_FILE"
    echo "  max_seconds:  $SEGMENT_MAX_SECONDS"
    echo "  output:       $SEGMENTS_DIR"
    echo ""

    python3 python/segment_audio.py \
        "$AUDIO_FILE" \
        --max-seconds "$SEGMENT_MAX_SECONDS" \
        --output-dir "$SEGMENTS_DIR"
fi


# --- Subset selection (optional) ---
if [[ -n "$MAX_SEGMENTS" ]]; then
    SWEEP_INPUT="$(mktemp -d)"
    trap 'rm -rf "$SWEEP_INPUT"' EXIT
    for f in $(ls "$SEGMENTS_DIR"/*.wav | head -n "$MAX_SEGMENTS"); do
        ln -s "$(realpath "$f")" "$SWEEP_INPUT/"
    done
    TOTAL=$(ls "$SEGMENTS_DIR"/*.wav | wc -l | tr -d ' ')
    echo ""
    echo "Using first $MAX_SEGMENTS of $TOTAL segments for steps 2-4"
else
    SWEEP_INPUT="$SEGMENTS_DIR"
fi


# ============================================================
# STEPS 2-4 — Loop over prompts
# ============================================================

PROMPTS=()
while IFS= read -r line; do
    PROMPTS+=("$line")
done < <(python3 -c "import json, sys; [print(p) for p in json.load(open(sys.argv[1]))]" "$PROMPT_FILE")
NUM_PROMPTS=${#PROMPTS[@]}
echo ""
echo "==== Prompt file: $PROMPT_FILE ($NUM_PROMPTS prompts) ===="

mkdir -p "$OUTPUT_DIR"

for ((i=0; i<NUM_PROMPTS; i++)); do
    PROMPT="${PROMPTS[$i]}"
    PROMPT_IDX=$(printf "%02d" $((i + 1)))
    OUTDIR="${OUTPUT_DIR}/prompt${PROMPT_IDX}_sweep_init_noise_level_${TIMESTAMP}"

    echo ""
    echo "============================================================"
    echo "  Prompt $PROMPT_IDX/$NUM_PROMPTS: \"$PROMPT\""
    echo "  Output: $OUTDIR"
    echo "============================================================"

    # --- STEP 2: Parameter sweep ---
    echo ""
    echo "---- Step 2: interpolateGen.py — init_noise_level sweep ----"

    python3 python/interpolateGen.py \
        --init-audio "$SWEEP_INPUT" \
        --prompt "$PROMPT" \
        --outdir "$OUTDIR" \
        --param init_noise_level \
        --start 0.6 \
        --end 0.75 \
        -n "$SWEEP_N" \
        --steps 15 \
        --cfg_scale 1 \
        --sampler_type pingpong \
        --match-source-length

    # --- STEP 3: Organize by noise level and concatenate ---
    echo ""
    echo "---- Step 3: Noise-level organize + concatenate ----"

    python3 SomaxCorpusWork/pythonScripts/workflow_noise_level_concat.py \
        "$OUTDIR" \
        --noise-levels "$SWEEP_N"

    # --- STEP 4: Flatten this run’s concatenated/ WAVs to OUTPUT_DIR root ---
    echo ""
    echo "---- Step 4: bringConcatenationsToParent.py ----"

    python3 python/bringConcatenationsToParent.py "$OUTDIR" --dest "$OUTPUT_DIR"

done

echo ""
echo "==== Pipeline complete — $NUM_PROMPTS prompt(s) processed ===="



