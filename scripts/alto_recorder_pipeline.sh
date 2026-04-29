#!/usr/bin/env bash
#
# alto_recorder_pipeline.sh
#
# Three-stage pipeline:
#   1. Segment a Somax2 corpus into individual WAV files
#   2. Run interpolateGen.py (init_noise_level sweep) on each segment
#   3. Organize outputs by noise level and concatenate
#
# Usage:
#   bash scripts/alto_recorder_pipeline.sh

set -euo pipefail

PROJ_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJ_ROOT"

# --- Paths ---
AUDIO_FILE="SomaxCorpusWork/Corpora/MultiCorpus2_alto-rec/alto_recorder_UNT.wav"
PICKLE_FILE="SomaxCorpusWork/Corpora/MultiCorpus2_alto-rec/alto_recorder_UNT.pickle"
SEGMENTS_DIR="SomaxCorpusWork/Corpora/MultiCorpus2_alto-rec/alto_recorder_UNTSegments"
PROMPT_FILE="scripts/alto_recorder_prompts.json"
OUTPUT_DIR="Audio/output"


# ============================================================
# STEP 1 — Segment the Somax2 corpus
# ============================================================
echo "==== STEP 1: Segmenting corpus ===="
echo "  audio:   $AUDIO_FILE"
echo "  pickle:  $PICKLE_FILE"
echo "  output:  $SEGMENTS_DIR"
echo ""

python SomaxCorpusWork/pythonScripts/segment_corpus.py \
    "$AUDIO_FILE" \
    "$PICKLE_FILE" \
    "$SEGMENTS_DIR"


# ============================================================
# STEP 2 — Parameter sweep with interpolateGen.py
# ============================================================
#
# TODO: interpolateGen.py does NOT currently support --prompt-file.
#       The --prompt-file flag exists in sampleReplace.py but has not
#       been ported to interpolateGen.py yet. Until it is added, replace
#       the --prompt-file line below with a single --prompt, e.g.:
#           --prompt "alto recorder, acoustic woodwind tone" \
#
echo ""
echo "==== STEP 2: interpolateGen.py — init_noise_level sweep ===="
echo "  init-audio:  $SEGMENTS_DIR"
echo "  prompt-file: $PROMPT_FILE"
echo ""

python python/interpolateGen.py \
    --init-audio "$SEGMENTS_DIR" \
    --prompt-file "$PROMPT_FILE" \
    --param init_noise_level \
    --start 0.1 \
    --end 0.9 \
    -n 5 \
    --steps 8 \
    --cfg_scale 1 \
    --sampler_type pingpong \
    --match-source-length


# ============================================================
# STEP 3 — Organize by noise level and concatenate
# ============================================================
#
# NOTE: interpolateGen.py writes ALL outputs into Audio/output/
# (a shared flat directory). It does not create a per-run subfolder.
# This means:
#   - Audio/output/ may already contain files from previous runs.
#   - workflow_noise_level_concat.py will process everything it finds
#     in that directory, not just the files from step 2.
#
# Possible future fixes:
#   a) Add an --outdir flag to interpolateGen.py so each run gets
#      its own output folder.
#   b) Clear Audio/output/ before step 2 (risky if you want to
#      keep old outputs).
#   c) Filter by timestamp or filename pattern before step 3.
#
echo ""
echo "==== STEP 3: Noise-level organize + concatenate ===="
echo "  input:  $OUTPUT_DIR"
echo ""

python SomaxCorpusWork/pythonScripts/workflow_noise_level_concat.py \
    "$OUTPUT_DIR" \
    --noise-levels 5


echo ""
echo "==== Pipeline complete ===="
