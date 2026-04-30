# Running on a Windows PC

This project is developed on macOS but designed to run batch generation jobs on a Windows PC with an NVIDIA GPU. Code lives in a **Git** clone on the PC; audio input and output sync through **Dropbox**.

## Architecture

```
MacBook (editing)                         PC Desktop (generation)
─────────────────                         ──────────────────────
Dropbox/…/StableAudioWorkspace/           D:\Repos\StableAudioWorkspace\  ← git clone
  python/  ──── git push ──────────────►    python/
  scripts/ ──── git push ──────────────►    scripts/
  Audio/output/  ◄── Dropbox sync ─────    Audio/output/ → symlink to Dropbox
  SomaxCorpusWork/Corpora/ ◄── Dropbox ─    SomaxCorpusWork/Corpora/ → symlink to Dropbox
```

- **Code** flows through Git (push on Mac, pull on PC).
- **Audio** flows through Dropbox (output syncs back to Mac automatically).
- The two never interfere — you can edit on Mac while the PC runs overnight.

## Prerequisites

- **Python 3.11+** — download from [python.org](https://www.python.org/downloads/)
- **NVIDIA GPU drivers** and **CUDA Toolkit** — download from [developer.nvidia.com](https://developer.nvidia.com/cuda-downloads)
- **Git for Windows** — download from [gitforwindows.org](https://gitforwindows.org/) (includes Git Bash, which is needed to run `.sh` scripts)
- **Dropbox** desktop app, syncing the same account as the Mac

## Step 1: Clone the Repo

Open Git Bash (installed with Git for Windows) and clone to a directory outside Dropbox:

```bash
cd /d/Repos    # or wherever you want the clone
git clone https://github.com/branlsnyder/SAOScripts.git StableAudioWorkspace
cd StableAudioWorkspace
```

## Step 2: Create a Virtual Environment

Virtual environments are platform-specific — the Mac venv will not work on Windows. Create a separate one:

```bash
python -m venv venv
source venv/Scripts/activate    # Git Bash activation path

# Install CUDA-enabled PyTorch first
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Then install everything else (pip skips torch since it's already installed)
pip install -r requirements.txt
```

> **Note:** The `--index-url` flag ensures you get the CUDA-enabled PyTorch build. Without it pip installs the CPU-only version and generation will be extremely slow.

## Step 3: Authenticate with Hugging Face

Model downloads require a Hugging Face access token. Run this once:

```bash
huggingface-cli login
```

Generate a token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) if you don't have one.

## Step 4: Create Symlinks to Dropbox

The scripts write output to `Audio/output/` using relative paths. On the Mac this directory is inside Dropbox naturally. On the PC the git clone is in a separate location, so you need symlinks that bridge the two.

Replace `D:\Dropbox\docs-d\04_Repos\CREATIVE WORK REPOS\StableAudioWorkspace` below with your actual Dropbox path.

### In Git Bash

```bash
cd /d/Repos/StableAudioWorkspace

# Audio output → Dropbox
mkdir -p Audio
ln -s "/d/Dropbox/docs-d/04_Repos/CREATIVE WORK REPOS/StableAudioWorkspace/Audio/output" Audio/output

# Corpus input → Dropbox (if you use Somax corpus scripts)
mkdir -p SomaxCorpusWork
ln -s "/d/Dropbox/docs-d/04_Repos/CREATIVE WORK REPOS/StableAudioWorkspace/SomaxCorpusWork/Corpora" SomaxCorpusWork/Corpora
```

### Or in an Administrator Command Prompt

```cmd
cd /d D:\Repos\StableAudioWorkspace

mkdir Audio
mklink /D Audio\output "D:\Dropbox\docs-d\04_Repos\CREATIVE WORK REPOS\StableAudioWorkspace\Audio\output"

mkdir SomaxCorpusWork
mklink /D SomaxCorpusWork\Corpora "D:\Dropbox\docs-d\04_Repos\CREATIVE WORK REPOS\StableAudioWorkspace\SomaxCorpusWork\Corpora"
```

> **Windows symlinks** require either **Developer Mode** enabled (Settings → For developers → Developer Mode) or running the terminal as Administrator. This is a one-time setup.

Both `Audio/` and `SomaxCorpusWork/Corpora/` are in `.gitignore`, so Git won't track the symlinks.

### Verify

```bash
ls -la Audio/output          # should show -> /d/Dropbox/…
ls -la SomaxCorpusWork/Corpora  # should show -> /d/Dropbox/…
```

## Step 5: Download Models

```bash
source venv/Scripts/activate
python setup/downloadModelSmall.py    # ~400 MB
# python setup/downloadModel.py      # ~3 GB large model (optional)
```

Model weights are cached in `~/.cache/huggingface/` and only need to be downloaded once.

## Step 6: Test

```bash
python python/testGen.py
```

Check that a `.wav` file appears in your Dropbox `Audio/output/` folder (and eventually syncs to your Mac).

## Running Shell Scripts on Windows

The `.sh` pipeline scripts use bash features (arrays, process substitution, `mktemp`, etc.) that don't work in Command Prompt or PowerShell. Use **Git Bash** instead:

```bash
source venv/Scripts/activate
bash scripts/alto_recorder_pipeline.sh
```

## Overnight Batch Runs

### Manual

1. Open Git Bash
2. Pull latest code: `git pull`
3. Activate the venv: `source venv/Scripts/activate`
4. Run the pipeline: `bash scripts/alto_recorder_pipeline.sh`
5. Output syncs to your Mac via Dropbox when finished

### Scheduled (Windows Task Scheduler)

Create a `.bat` file (e.g. `run_overnight.bat`) that wraps the bash call:

```bat
@echo off
"C:\Program Files\Git\bin\bash.exe" -c "cd '/d/Repos/StableAudioWorkspace' && source venv/Scripts/activate && git pull && bash scripts/alto_recorder_pipeline.sh"
```

Then in Task Scheduler:

1. Create a new task
2. **Trigger:** set your desired start time (e.g. 11:00 PM)
3. **Action:** Start a program → browse to `run_overnight.bat`
4. **Conditions:** uncheck "Start only if on AC power"; check "Wake the computer"
5. **Settings:** check "Run task as soon as possible after a scheduled start is missed"

## Day-to-Day Workflow


| When         | Where | What                                         |
| ------------ | ----- | -------------------------------------------- |
| Daytime      | Mac   | Edit scripts, tweak prompts, test quick runs |
| Before run   | Mac   | `git push`                                   |
| Evening      | PC    | `git pull`, then start the batch script      |
| Overnight    | PC    | GPU generates audio; output lands in Dropbox |
| Next morning | Mac   | Output has synced — listen, iterate, repeat  |


## Troubleshooting


| Issue                                           | Fix                                                                                       |
| ----------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `ln -s` fails with permission error             | Enable Developer Mode or run Git Bash / cmd as Administrator                              |
| `torch.cuda.is_available()` returns `False`     | Reinstall PyTorch with the CUDA index URL (see Step 2)                                    |
| `ModuleNotFoundError: stable_audio_tools`       | Activate the venv first: `source venv/Scripts/activate`                                   |
| Scripts crash with `python3: command not found` | On Windows, use `python` instead of `python3`, or create an alias: `alias python3=python` |
| Dropbox conflict files appear                   | Make sure you only edit code on Mac and only run on PC; pull via Git, not Dropbox         |


