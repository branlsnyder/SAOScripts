# Stable Audio Open — Scripts

Command-line tools for audio generation using [Stable Audio Open](https://huggingface.co/stabilityai/stable-audio-open-small) (small and large models). Supports **text-to-audio** generation from text prompts and **audio-to-audio** resynthesis that transforms existing audio guided by a text prompt.

Built on top of [stable-audio-tools](https://github.com/Stability-AI/stable-audio-tools) by Stability AI.

## Setup

**Requirements:** Python 3.11+, a [Hugging Face](https://huggingface.co/) account with access to the Stable Audio Open model(s).

```bash
# Clone and create a virtual environment
git clone https://github.com/branlsnyder/SAOScripts.git
cd SAOScripts
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download a model (requires HF authentication — run `huggingface-cli login` first)
python setup/downloadModelSmall.py   # ~400 MB small model
# or
python setup/downloadModel.py        # larger model (~3 GB)
```

## Scripts

### sampleReplace.py - Generates Audio in Batches (e.g. for generating a variant of an audio corpus)

Supports two modes depending on whether `--indir` is provided.

**Text-to-audio** — generate audio from a prompt:

```bash
python python/sampleReplace.py --prompt "solo violin music" -n 3 --duration 10
```

**Audio-to-audio** — restyle existing audio files guided by a prompt:

```bash
python python/sampleReplace.py --indir my_samples --prompt "warm analog pad" --noise-level 0.3
```

The `--noise-level` flag (0–1) controls how much the output departs from the original:

| Range   | Effect                                           |
| ------- | ------------------------------------------------ |
| 0.1–0.2 | Very close to original (subtle restyling)        |
| 0.3–0.5 | Moderate departure (new texture, same structure) |
| 0.6–0.8 | Substantial regeneration (loose structural echo) |

Per-file prompts can be supplied via a JSON map:

```bash
python python/sampleReplace.py --indir my_samples --prompt-file prompts.json
```

<details>
<summary>Full options reference</summary>

| Flag             | Default                   | Description                                                                       |
| ---------------- | ------------------------- | --------------------------------------------------------------------------------- |
| `--model`        | `stable-audio-open-small` | Which model to use (`stable-audio-open-small` or `stable-audio-open`)             |
| `--indir`        | _(none)_                  | Input directory of audio files. If omitted, runs in text-to-audio mode            |
| `--outdir`       | `Audio/output/`           | Output directory                                                                  |
| `--prompt`       | _(none)_                  | Text prompt (required for text-to-audio; applied to every file in audio-to-audio) |
| `--prompt-file`  | _(none)_                  | JSON file mapping filenames to prompts (audio-to-audio only)                      |
| `--noise-level`  | `0.3`                     | Init noise level 0–1 (audio-to-audio only)                                        |
| `--steps`        | `8`                       | Number of diffusion steps                                                         |
| `--cfg-scale`    | `1.0`                     | Classifier-free guidance scale (`stable-audio-open` only)                         |
| `--sampler-type` | `pingpong`                | Sampler type                                                                      |
| `--seed`         | `-1`                      | Random seed (`-1` for random)                                                     |
| `--duration`     | _(auto)_                  | Output duration in seconds                                                        |
| `-n`             | `1`                       | Number of files to generate (text-to-audio only)                                  |

</details>

### interpolateGen.py — Generates batch of audio interpolating across a given parameter

Generates multiple outputs while linearly sweeping a single parameter (e.g. `cfg_scale`, `steps`, `init_noise_level`) across a range. Useful for exploring how a parameter affects output character. `--init-audio` accepts a single file **or a folder** of audio files for batch processing (the sweep is run independently for each file, with the model loaded only once).

```bash
# Sweep CFG scale from 0 to 15 in 5 steps
python python/interpolateGen.py --prompt "warm analog pad" --param cfg_scale --start 0 --end 15 -n 5

# Audio-to-audio: sweep noise level on an input file
python python/interpolateGen.py --init-audio my_loop.wav --prompt "dreamy pads" --param init_noise_level --start 0.1 --end 0.9 -n 5

# Batch audio-to-audio: sweep across every file in a folder
python python/interpolateGen.py --init-audio my_samples/ --prompt "dreamy pads" --param init_noise_level --start 0.1 --end 0.9 -n 5

# Trim outputs to match each source file's duration
python python/interpolateGen.py --init-audio my_samples/ --prompt "dreamy pads" --param init_noise_level --start 0.1 --end 0.9 -n 5 --match-source-length
```

<details>
<summary>Full options reference</summary>

| Flag                    | Default                   | Description                                                                                     |
| ----------------------- | ------------------------- | ----------------------------------------------------------------------------------------------- |
| `--model`               | `stable-audio-open-small` | Which model to use                                                                              |
| `--prompt`              | `dubstep bass growls`     | Text prompt                                                                                     |
| `--param`               | `cfg_scale`               | Parameter to sweep (`cfg_scale`, `steps`, `sigma_min`, `sigma_max`, `init_noise_level`, `seed`) |
| `--start`               | `0`                       | Start value                                                                                     |
| `--end`                 | `15`                      | End value                                                                                       |
| `-n`                    | `5`                       | Number of outputs                                                                               |
| `--init-audio`          | _(none)_                  | Audio file **or folder** for audio-to-audio mode                                                |
| `--init_noise_level`    | `0.3`                     | Noise level for audio-to-audio (when not sweeping it)                                           |
| `--match-source-length` | `false`                   | Trim each output to match its source file's duration (audio-to-audio only)                      |
| `--steps`               | `8`                       | Diffusion steps (when not sweeping)                                                             |
| `--cfg_scale`           | `1`                       | CFG scale (when not sweeping)                                                                   |
| `--seed`                | `-1`                      | Random seed                                                                                     |
| `--duration`            | `11`                      | Output duration in seconds                                                                      |

</details>

### testGen.py — generates a single audio, for testing

Minimal script to verify the model loads and generates output.

```bash
python python/testGen.py
python python/testGen.py --model stable-audio-open
```

### Utility modules

| Script                  | Purpose                                                                                                  |
| ----------------------- | -------------------------------------------------------------------------------------------------------- |
| `python/audio_utils.py`        | Shared model loading and audio post-processing (used by all generation scripts)                          |
| `python/output_naming.py`      | Centralized output naming — all scripts write to `Audio/output/` with descriptive, timestamped filenames |
| `setup/downloadModel.py`      | Downloads `stable-audio-open-1.0` (large model) from Hugging Face                                        |
| `setup/downloadModelSmall.py` | Downloads `stable-audio-open-small` from Hugging Face                                                    |

## Shell Scripts

Multi-step workflows that chain Python scripts into reusable pipelines live in `scripts/`. Each script captures the full sequence — inputs, parameters, and orchestration — in a single file.

```bash
source venv/bin/activate
bash scripts/alto_recorder_pipeline.sh
```

See [`Documentation/shell_scripts.md`](Documentation/shell_scripts.md) for details on writing and running these scripts, including looping over prompt files and timestamping output directories.

## Notes on models

Generation scripts accept `--model stable-audio-open-small` (default) or `--model stable-audio-open`. However, `stable-audio-open` is **not fully functional** in this repo at the moment. **Stick with `stable-audio-open-small` for now.**

The small model uses ARC post-training with a contrastive discriminator loss that replaces Classifier-Free Guidance (CFG). The `--cfg-scale` flag only has an effect with the large model. See [Novack et al. 2025](https://arxiv.org/abs/2505.08175) for details.

## License

The scripts in this repo are provided as-is. The Stable Audio Open models are subject to [Stability AI's licensing terms](https://huggingface.co/stabilityai/stable-audio-open-small).
