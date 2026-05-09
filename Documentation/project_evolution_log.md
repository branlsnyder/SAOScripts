# Project evolution — first-person session log

I’m writing this for you like I’d explain it across the table: session by session, what I changed, **what audio went in and out**, **exact prompts**, and **commands you could paste**. My corpus and renders still live under `**Audio/`** and `**SomaxCorpusWork/Corpora/**` (gitignored), so you won’t see the WAV bytes in Git—only paths and filenames as I wired them into scripts.

Across pipelines I kept the same choreography: `**segment_corpus.py**` peels a Somax2 `**.wav` + `.pickle**` into segment WAVs, `**python/interpolateGen.py**` does an `**init_noise_level` sweep** in audio-to-audio mode with `**--match-source-length`**, and `**workflow_noise_level_concat.py**` buckets by noise tier and emits `**concatenated/1_noise_level-….wav**`-style mixes. Outputs land under `**Audio/output/…**` with names `**python/output_naming.py**` builds (tiny model tag `**sm**`, `**s15**` for fifteen steps, `**pp**` for ping-pong sampler, timestamps, etc.—you’ve seen `**wail-augmented-5xstr_sm_swinit_noise_level-0.6_nl0.6_s15_cfg1_pp_d11_***` style files when you run the wail rigs).

Stable Audio pulls `**stabilityai/stable-audio-open-small**` in my traces at **44.1 kHz** with a reported cap near **11.89 s**; my wail clips sit around **~10 s** so `**--match-source-length`** trims generations back before concat. On CPU I always get benign noise: `**flash_attn` optional**, `**torch.cuda.amp` disabled**, `**clip`** nagging about `**pkg_resources**`.

Below, **Git** hashes are breadcrumbs if you want to bisect—the story is chronological.

---

### Session — April 21, morning (cold start)

I stood the repo up with the Python CLIs `**interpolateGen.py`**, `**sampleReplace.py**`, `**testGen.py**`, `**output_naming.py**`, `**downloadModel.py**`, `**downloadModelSmall.py**`, `**requirements.txt**`, plus `**Docs.md**`. I checked in `**2505.08175v3.pdf**` (later renamed `**stableAudioOpenSmall_Paper.pdf**` in `**Documentation/**`). I set `**.gitignore**` so `**Audio/**`, `***.wav**`, model weights, and secrets stay local, and `**.gitattributes**` for sane line endings.

**Commands you’d still use:** after a venv, `pip install -r requirements.txt` (later superseded partly by `**pyproject.toml`**), then e.g. `python setup/downloadModelSmall.py` or `python setup/downloadModel.py` with Hugging Face auth.

*(Git: `622a0cf`)*  

I also slipped in an agent-oriented Hugging Face skill under `**.agents/skills/hf-cli/*`* · *(Git: `2f052e3`)*

---

### Session — April 21 (README and packaging)

I wrote `**README.md*`* so cloning is obvious—clone, `**python -m venv venv**`, `**source venv/bin/activate**`, install, pull a model `**setup/downloadModelSmall.py**` / `**setup/downloadModel.py**`, run `**python/python/sampleReplace.py**` or `**python/python/interpolateGen.py**`. Examples I still rely on verbally:

```bash
python python/sampleReplace.py --prompt "solo violin music" -n 3 --duration 10
python python/sampleReplace.py --indir my_samples --prompt "warm analog pad" --noise-level 0.3
```

*(Git: `9563c19`)*

Then I formalized `**pyproject.toml*`* (`stable-audio-scripts`, `**stable-audio-tools==0.0.19**`, Python ≥3.11), centralized inference bits in `**python/audio_utils.py**`, and tightened `**python/output_naming.py**` and `**--outdir**`.

*(Git: `704cf9b`, `43cd100`)*  

Later, over Cursor, I dug through `**generate_diffusion_cond*`* in `**python/testGen.py**` with someone— `**6788a62e-b6df-467e-92a6-a1da34378716**`.

---

### Session — April 23 (folder batch interpolation)

I taught `**python/interpolateGen.py**` to take `**--init-audio**` as either a single file **or an entire folder** so I could sweep `**init_noise_level`** across every corpus clip without reloading weights between files.

*(Git: `effa002`)*  

Example shape I still narrate aloud:

```bash
python python/interpolateGen.py --init-audio my_samples/ --prompt "dreamy pads" \
  --param init_noise_level --start 0.1 --end 0.9 -n 5 --match-source-length
```

---

### Session — April 29 (segments without the model)

I added `**python/segment_audio.py**` for non-Somax chopping—equal cores up to `**--max-seconds**` (default ties to Stable Audio horizons), optional overlap `**--overlap-ms**`:

```bash
python python/segment_audio.py long_take.wav --max-seconds 11 --output-dir segments/
```

**Audio path:** arbitrary long input `**long_take.wav`**, outputs land beside it or under `**segments/**`.

*(Git: `10b7feb`)*

---

### Session — April 29 (Somax tooling + first shell pipelines)

I moved Python into `**python/*`*, installers into `**setup/**`, slid `**Docs.md**` into `**Documentation/Docs.md**`, and ported **SomaxCorpusWork**—`**segment_corpus.py`**, `**concat_segments.py**`, `**organize_by_noise_level.py**`, `**workflow_batch_concat.py**`, `**workflow_noise_level_concat.py**`, plus corpus notes PDFs/PDF user guide/`maxpat`.

I authored `**scripts/alto_recorder_pipeline.sh**` chaining:

**Inputs:** `**SomaxCorpusWork/Corpora/MultiCorpus2_alto-rec/alto_recorder_UNT.wav`** + `**alto_recorder_UNT.pickle**` → `**alto_recorder_UNTSegments/**`  
**Prompts:** JSON array `**scripts/alto_recorder_prompts.json`** (eight lines: alto recorder warmth, ethereal winds, dubstep growl, distressed countertenor wail, dry jazz drums, techno kit, fiddle, metal Wall).  
**Generation:** `**interpolateGen.py`** with `**--start 0.6**` `**--end 0.9**`, `**-n 2**` (two `**init_noise_level**` stops—I keep `**SWEEP_N**` matching `**workflow_noise_level_concat.py --noise-levels**`), `**--steps 2**`, `**--match-source-length**`  
**Outputs:** per-prompt dirs `**Audio/output/prompt##_sweep_init_noise_level_<timestamp>/`**, concat under each folder’s `**concatenated/**`  
**Kickoff:**

```bash
bash scripts/alto_recorder_pipeline.sh
```

Later I cloned the pattern as `**scripts/alto_recorder_pipeline_15step.sh**` where the only substantive change was `**--steps 15**` on `**interpolateGen.py**`.

*(Git: `f9ccbc3`, `**Documentation/*`* stabilized in `acb269a`, alto 15-step in `8322e83`)*  

I drafted `**Documentation/shell_scripts.md*`*, `**setup.md**`, `**noise_level_vs_steps.md**` to explain `**SWEEP_N` vs `-n**` and why `**--noise-levels**` must track.

---

### Session — April 29 (silence remover)

Someone asked Cursor for preprocessing that strips silence longer than `**--min-silence**` (default **1 s**) before corpus work. I landed `**SomaxCorpusWork/pythonScripts/remove_silence.py`**—standard-library WAV slicing, `**--threshold**`, folder mode with `**--outdir**`.

**Example shim before segmentation:**

```bash
python3 SomaxCorpusWork/pythonScripts/remove_silence.py \
  SomaxCorpusWork/Corpora/MultiCorpus2_alto-rec/alto_recorder_UNT.wav \
  SomaxCorpusWork/Corpora/MultiCorpus2_alto-rec/alto_recorder_UNT_no_silence.wav \
  --min-silence 1.0
```

*(Git: `0a217ab` · Cursor thread `dec890f7-4bb7-43cb-838b-2c11f4d15e4d`)*

---

### Session — April 30 (concat edge cases, PC playbook, heavy GEC rigs)

Git `**0f5e769*`* expanded `**SomaxCorpusWork/pythonScripts/concat_segments.py**`—when `**segment*.wav**` doesn’t glob, sort lexically instead—and I wrote `**Documentation/pc_setup.md**` after I spelled out Dropbox + GitHub splits with you: code repo on Git, `**Audio/**` outside on Dropbox, Git Bash `**bash scripts/…**` on Windows overnight.

Concurrently `**scripts/gecVoxFull_pipeline_15step.sh**` hard-wires `**MutliCorpus3_gecVox/gecVoxFull_no_silence.wav**` + `**.pickle**` → `**gecVoxFull_no_silenceSegments/**`, `**scripts/gecVoxFull_prompts.json**` (**autotune**, airy orchestral, dub bass, distressed male wail, woody jazz drums, techno kit, scratchy fiddle, extreme metal sweep), `**MAX_SEGMENTS=40`**, `**SWEEP_N=10**` (so `**init_noise_level` sweep 0.3→0.9 with ten taps**):

```bash
python3 python/interpolateGen.py \
  --init-audio "$SWEEP_INPUT" \
  --prompt "$PROMPT" \
  --outdir "$OUTDIR" \
  --param init_noise_level --start 0.3 --end 0.9 \
  -n 10 \
  --steps 15 \
  --cfg_scale 1 \
  --sampler_type pingpong \
  --match-source-length
python3 SomaxCorpusWork/pythonScripts/workflow_noise_level_concat.py "$OUTDIR" --noise-levels 10
```

I patched pipeline paths `**90bfa96**` and, while a run spun, tweaked noise-bin counts so `**--noise-levels**` always matched interpolate `**-n**`— `**1bd86662-f3f2-40b9-b02a-fd886e02448b**`.

`**scripts/gecVoxFullSMALL_pipeline_15step.sh**` is the variant pointed at `**gecVoxFull_no_silenceSegmentsSmall**`; as checked in, STEP 1’s `**AUDIO_FILE**` lines are **commented**—I personally treat it as **“reuse a prebuilt small segment folder.”**

---

### Session — April 30 (pad everything to one reference duration)

Someone needed every clip in `**MutliCorpus3_gecVox/…butterfly-sweep**` padded to `**gecVoxFull_no_silence.wav`’**s length. `**SomaxCorpusWork/pythonScripts/pad_to_reference_duration.py`** does that now:

```bash
python SomaxCorpusWork/pythonScripts/pad_to_reference_duration.py \
  SomaxCorpusWork/Corpora/MutliCorpus3_gecVox/gecVoxFull_no_silence.wav \
  SomaxCorpusWork/Corpora/MutliCorpus3_gecVox/1-8_butterfly-sweep_39segs_silencepadded \
  --outdir SomaxCorpusWork/Corpora/MutliCorpus3_gecVox/padded_out
```

*(Git: `b6a59c7` · spec chat `182f785d-8729-473f-b6ef-40ca1fedd1c8`)*

---

### Session — April 30 (human ops)

We talked through closing a laptop lid during long bash pipelines—mostly “sleep freezes work; park it on desktop / `caffeinate` etc.” (`**ce30ed9e-db89-4561-8921-3f0883220ff1*`*). No code moved.

Somax-region Max questions lived in `**06f1d909-f0bb-4688-add8-6e9c56f79ec6**`.

---

### Session — May 8 (finally documented `segment_audio`)

I spelled out `**python/segment_audio.py**` inside `**Documentation/Docs.md**` after you asked whether the ten-ish-second splitter was written down (`**95cc9eb5-7696-4c9e-9e78-40142282a7d1**`).

*(Git: `f9639c1`)*

---

### Session — May 8 (the wail rigs + what I actually ran)

I checked in `**scripts/WailStretchSMALL_pipeline_curated.sh*`* and `**scripts/WailStretchSMALL_pipeline.sh**`. Conceptually:

**Corpus notion:** `**MultiCorpus4_wail`** with segments under `**SomaxCorpusWork/Corpora/MultiCorpus4_wail/Segments_wail_augmented_5xStretched**` (clips like `**wail_augmented_5xStretched_seg001.wav` …**)  
**Prompt JSONs:**

- `**scripts/stable_audio_prompts_curated.json`** — forty-three long Stable-Audio-ish descriptions (genre/Mood/SFX-spanning—from thrash hybrids to orchestral cues to ringtone mocks).  
- `**scripts/wailStretch_prompts.json**` / `**scripts/wailStretch_prompts_2.json**` — seven shorter lines each; **_2** appends `**300 BPM`** to every string for experimentation.

Curated runner points `**PROMPT_FILE="scripts/stable_audio_prompts_curated.json"**`. The non-curated file I last saved points `**scripts/wailStretch_prompts_2.json**` and nests `**OUTDIR="Audio/output/wailStretch300BPMtest/prompt##_…"**`.

**Sweep parameters I standardized there:** `**init_noise_level`** from **0.6→0.9**, `**SWEEP_N=3`** (ties `**workflow_noise_level_concat.py --noise-levels 3**`), `**--steps 15**`, `**--match-source-length**`, `**--sampler_type pingpong**`  
**Representative interpolate block:**

```bash
python3 python/interpolateGen.py \
  --init-audio "$SWEEP_INPUT" \
  --prompt "$PROMPT" \
  --outdir "$OUTDIR" \
  --param init_noise_level --start 0.6 --end 0.9 \
  -n 3 \
  --steps 15 \
  --cfg_scale 1 \
  --sampler_type pingpong \
  --match-source-length
```

Because `**bash**` runs with `**set -u**`, I added `**SKIP_SEGMENT_STEP=1**` so I can reuse pre-segmented dirs without uncommenting placeholders:

```bash
SKIP_SEGMENT_STEP=1 bash scripts/WailStretchSMALL_pipeline_curated.sh
SKIP_SEGMENT_STEP=1 bash scripts/WailStretchSMALL_pipeline.sh
```

When I messed up `**AUDIO_FILE` expansions**, you and I chased `**AUDIO_FILE: unbound variable`**—that fix lives in chats `**b6ff13ee-e768-4121-a029-b298ffd947f8**`.

**Terminal receipts I preserved:** `**terminals/1.txt`** exited **0** after **41 prompts** curated run (folders `**Audio/output/prompt{N}_sweep_init_noise_level_20260508_182717`**; concat outputs ~**1321074 frames / ~29.956 s each tier** stacking three trimmed ~**9.99 s** segments). `**terminals/8.txt`** exited **0** after **7** prompts into `**Audio/output/wailStretch300BPMtest/…20260508_185647`**—same acoustics fingerprint.

Concurrently `**f8786ab1-e549-46f5-af91-93ae9084c816**` was me iterating long-form prompts anchored on `**Documentation/stableAudioOpenSmall_Paper.pdf**`—that’s `**stable_audio_prompts_curated.json**`.

*(Git: `61c1d6b`)*

---

### Session — meta (you’re holding it)

Cursor helped me merge git + IDE captures into `**Documentation/project_evolution_log.md*`* (`**61f6b832-8558-4349-af90-28af1b1a4088**` and follow-ups)—this rewrite is me speaking that same ledger aloud to you instead of stacking appendices.

---

## Quick map — where binaries and corpora notionally plug in


| Script                                             | Canonical inputs (unless you flip vars)                                                                                                                 | Prompt list                                   | Outputs                                                                           |
| -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------- | --------------------------------------------------------------------------------- |
| `**scripts/alto_recorder_pipeline*.sh**`           | `**MultiCorpus2_alto-rec/alto_recorder_UNT.{wav,pickle}**` → `**alto_recorder_UNTSegments/**` · optional first **N** via `**MAX_SEGMENTS`** symlink tmp | `**scripts/alto_recorder_prompts.json**`      | `**Audio/output/prompt##_sweep_init_noise_level_<stamp>/**` + `**concatenated/**` |
| `**scripts/gecVoxFull_pipeline_15step.sh**`        | `**MutliCorpus3_gecVox/gecVoxFull_no_silence.{wav,pickle}**` → `**…Segments/**`, first **40** default                                                   | `**scripts/gecVoxFull_prompts.json`**         | same pattern (`**SWEEP_N=10**`, `**0.3–0.9**`)                                    |
| `**scripts/WailStretchSMALL_pipeline_curated.sh**` | `**Segments_wail_augmented_5xStretched**` (first **3** by default); optional `**SKIP_SEGMENT_STEP=1`**                                                  | `**stable_audio_prompts_curated.json**`       | flat `**Audio/output/prompt##_…**`                                                |
| `**scripts/WailStretchSMALL_pipeline.sh**`         | same corpus dir notion                                                                                                                                  | `**wailStretch_prompts_2.json**` *(as saved)* | nests under `**Audio/output/wailStretch300BPMtest/*`*                             |


---

## Keeping this conversational log honest

Whenever you rerun something material, jot the `**TIMESTAMP**` you saw echoed, the `**PROMPT_FILE**`, `**MAX_SEGMENTS**`, `**SWEEP_N**`, and if you chased any stderr about `**flash_attn**` / CUDA—we’re almost always documenting **routing** (`python/interpolateGen.py …`) **not** blobs in Git.