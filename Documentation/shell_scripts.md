# Shell Scripts

Shell scripts chain the Python tools in this repo into multi-step workflows. Rather than typing a sequence of commands into the terminal each time, a shell script captures the full pipeline — inputs, parameters, ordering — in a single reusable file.

## Why use shell scripts?

- **Reproducibility** — Every parameter and file path is recorded. You can re-run or tweak a workflow without remembering what you typed last time.
- **Multi-step orchestration** — A single script can run segmentation, generation, and post-processing in sequence, passing the output of one step as the input to the next.
- **Batch iteration** — Scripts can loop over a list of prompts, input files, or parameter sets, running the full pipeline for each one.
- **Work history** — Keeping scripts in `scripts/` (and committing them to git) gives you a log of what you've run and how.

## How it works

Each shell script lives in `scripts/` and follows the same general pattern:

1. **Set paths and parameters** at the top of the file as variables.
2. **Call Python scripts** (`python3 python/interpolateGen.py ...`, `python3 SomaxCorpusWork/pythonScripts/segment_corpus.py ...`, etc.) in sequence, wiring outputs from one step into the next.
3. **Loop** over prompts, files, or parameter ranges when batch processing is needed.

A prompt file (a JSON array of strings) can be used to drive batch generation across multiple prompts without changing the script itself.

### Example: `alto_recorder_pipeline.sh`

This script demonstrates the pattern with a three-stage pipeline:

1. **Segment** a Somax2 corpus into individual WAV files (`segment_corpus.py`).
2. **Generate** variations of each segment with a noise-level sweep (`interpolateGen.py`).
3. **Organize and concatenate** the outputs by noise level (`workflow_noise_level_concat.py`).

Steps 2–3 loop over every prompt in a JSON prompt file, so one run of the script produces a full set of outputs for each prompt.

```bash
# activate the venv first
source venv/bin/activate

# run the pipeline
bash scripts/alto_recorder_pipeline.sh
```

## Writing your own shell scripts

Start from the example or from scratch. The key ingredients:

```bash
#!/usr/bin/env bash
set -euo pipefail  # stop on errors

# navigate to project root
PROJ_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJ_ROOT"

# define your inputs and parameters as variables
INPUT="path/to/input.wav"
OUTDIR="Audio/output/my_run_$(date +%Y%m%d_%H%M%S)"

# call Python scripts in sequence
python3 python/someScript.py --input "$INPUT" --outdir "$OUTDIR"
python3 python/anotherScript.py "$OUTDIR"
```

To loop over prompts from a JSON file:

```bash
PROMPT_FILE="scripts/my_prompts.json"
PROMPTS=()
while IFS= read -r line; do
    PROMPTS+=("$line")
done < <(python3 -c "import json, sys; [print(p) for p in json.load(open(sys.argv[1]))]" "$PROMPT_FILE")

for ((i=0; i<${#PROMPTS[@]}; i++)); do
    PROMPT="${PROMPTS[$i]}"
    # ... run generation with --prompt "$PROMPT" ...
done
```

### Tips

- Use `python3`, not `python` — macOS does not provide a bare `python` command.
- Always activate the venv (`source venv/bin/activate`) before running a script, since the generation scripts depend on `stable_audio_tools`.
- Use `$(date +%Y%m%d_%H%M%S)` in output paths to timestamp each run and avoid overwriting previous results.
- The `set -euo pipefail` line at the top ensures the script stops immediately if any step fails, rather than silently continuing with missing inputs.
