# Setup and Getting Started

## Requirements

- Python 3.11+
- A [Hugging Face](https://huggingface.co/) account with access to the Stable Audio Open model(s)

## Installation

```bash
# Clone and create a virtual environment
git clone https://github.com/branlsnyder/SAOScripts.git
cd SAOScripts
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Hugging Face Authentication

Model downloads require Hugging Face authentication. Log in once before downloading:

```bash
huggingface-cli login
```

You'll be prompted for an access token. Generate one at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).

## Downloading Models

Two models are available. Both are downloaded via helper scripts in `setup/`:

```bash
# Small model (~400 MB) — recommended starting point
python setup/downloadModelSmall.py

# Large model (~3 GB) — supports Classifier-Free Guidance
python setup/downloadModel.py
```

All generation scripts default to the small model. Pass `--model stable-audio-open` to use the large model instead.

## Models at a Glance

| Model | Flag value | Size | CFG support |
|---|---|---|---|
| **Stable Audio Open Small** | `stable-audio-open-small` (default) | ~400 MB | No — uses ARC post-training instead |
| **Stable Audio Open** | `stable-audio-open` | ~3 GB | Yes — use `--cfg-scale` to control prompt adherence |

The small model uses ARC post-training with a contrastive discriminator loss that replaces Classifier-Free Guidance (CFG) for prompt adherence. The `--cfg-scale` / `--cfg_scale` flag only has an effect with the large model. See [Novack et al. 2025](https://arxiv.org/abs/2505.08175) for details.

## Project Structure

```
StableAudioWorkspace/
├── python/                   # Generation scripts and utilities
│   ├── sampleReplace.py      # Batch audio generation
│   ├── interpolateGen.py     # Parameter sweep generation
│   ├── testGen.py            # Smoke test
│   ├── audio_utils.py        # Shared model loading and post-processing
│   └── output_naming.py      # Centralized output naming convention
├── scripts/                  # Shell pipeline scripts
├── setup/                    # Model download scripts
│   ├── downloadModel.py      # Downloads stable-audio-open (large)
│   └── downloadModelSmall.py # Downloads stable-audio-open-small
├── Audio/
│   └── output/               # Default output directory for all scripts
├── Documentation/            # Project documentation
└── requirements.txt
```

## Quick Test

After setup, verify everything works:

```bash
python python/testGen.py
```

This generates a single audio file with a hardcoded prompt and saves it to `Audio/output/`. If it runs without errors, your environment is ready.
