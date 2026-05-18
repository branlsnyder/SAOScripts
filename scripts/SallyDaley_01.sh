
#!/usr/bin/env bash
#
# gecVoxFull_pipeline.sh
#
# Three-stage pipeline:
#   1. Segment a Somax2 corpus into individual WAV files
#   2-3. For each prompt in the prompt JSON file:
#        2. Run interpolateGen.py (init_noise_level sweep) on the segments
#        3. Organize outputs by noise level and concatenate
#
# Usage:
#   bash scripts/gecVoxFull_pipeline.sh

set -euo pipefail

PROJ_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJ_ROOT"

# --- Paths ---
# Step 1 needs these Somax2 sources (uncomment + fix paths). If SEGMENTS_DIR is already filled
# with .wav files from a prior run, skip step 1: SKIP_SEGMENT_STEP=1 bash scripts/...
SKIP_SEGMENT_STEP="${SKIP_SEGMENT_STEP:-0}"
# AUDIO_FILE="SomaxCorpusWork/Corpora/MultiCorpus4_wail/<your_corpus>.wav"
# PICKLE_FILE="SomaxCorpusWork/Corpora/MultiCorpus4_wail/<your_corpus>.pickle"
SEGMENTS_DIR="/Users/brandonwoosnyder/Dropbox/docs-d/04_Repos/CREATIVE WORK REPOS/StableAudioWorkspace/SomaxCorpusWork/Corpora/MultiCorpus5_SallyDaley/SallySegements"
PROMPT_FILE="/Users/brandonwoosnyder/Dropbox/docs-d/04_Repos/CREATIVE WORK REPOS/StableAudioWorkspace/scripts/music51_01_prompts.json" 
MAX_SEGMENTS=""  # leave empty for all segments, or set e.g. "5" for quick iteration
SWEEP_N=8  # init_noise_level samples; must match --noise-levels in step 3
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"


# ============================================================
# STEP 1 — Segment the Somax2 corpus (runs once)
# ============================================================
if [[ "$SKIP_SEGMENT_STEP" == "1" ]]; then
    echo "==== STEP 1: skipped (SKIP_SEGMENT_STEP=1) ===="
    echo "  using existing segments in: $SEGMENTS_DIR"
    echo ""
elif [[ -z "${AUDIO_FILE:-}" || -z "${PICKLE_FILE:-}" ]]; then
    echo "AUDIO_FILE / PICKLE_FILE are unset. Uncomment them under \"--- Paths ---\","
    echo "or skip segmentation when SEGMENTS_DIR already has clips: SKIP_SEGMENT_STEP=1" >&2
    exit 1
else
    echo "==== STEP 1: Segmenting corpus ===="
    echo "  audio:   $AUDIO_FILE"
    echo "  pickle:  $PICKLE_FILE"
    echo "  output:  $SEGMENTS_DIR"
    echo ""

    python3 SomaxCorpusWork/pythonScripts/segment_corpus.py \
        "$AUDIO_FILE" \
        "$PICKLE_FILE" \
        "$SEGMENTS_DIR"
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
    echo "Using first $MAX_SEGMENTS of $TOTAL segments for steps 2-3"
else
    SWEEP_INPUT="$SEGMENTS_DIR"
fi


# ============================================================
# STEPS 2-3 — Loop over prompts
# ============================================================

PROMPTS=()
while IFS= read -r line; do
    PROMPTS+=("$line")
done < <(python3 -c "import json, sys; [print(p) for p in json.load(open(sys.argv[1]))]" "$PROMPT_FILE")
NUM_PROMPTS=${#PROMPTS[@]}
echo ""
echo "==== Prompt file: $PROMPT_FILE ($NUM_PROMPTS prompts) ===="

for ((i=0; i<NUM_PROMPTS; i++)); do
    PROMPT="${PROMPTS[$i]}"
    PROMPT_IDX=$(printf "%02d" $((i + 1)))
    OUTDIR="Audio/output/prompt${PROMPT_IDX}_sweep_init_noise_level_${TIMESTAMP}"

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
        --start 0.5 \
        --end 0.9 \
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

done

echo ""
echo "==== Pipeline complete — $NUM_PROMPTS prompt(s) processed ===="



# NOTES: this is a nice way to create many branching pathways from a faithful start. the step size is low which makes it quite chaotic and undefined in its envelope.