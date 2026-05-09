# Project evolution — first-person session log

<!-- Subjective “why” lines use Markdown blockquotes (`> …`) so they stay visible in Cursor preview and plain Markdown viewers without HTML/CSS. -->

I’m writing this for you like I’d explain it across the table: session by session, what I changed, **what audio went in and out**, **exact prompts**, and **commands you could paste**. My corpus and renders still live under **`Audio/`** and **`SomaxCorpusWork/Corpora/`** (gitignored), so you won’t see the WAV bytes in Git—only paths and filenames as I wired them into scripts.

> **Why:** I wanted a written trail you (or future me) can follow without staring at blobs in Git—I care more about repeatable routing than checking in gigabytes.

Across pipelines I kept the same choreography: **`SomaxCorpusWork/pythonScripts/segment_corpus.py`** peels a Somax2 **`.wav` + `.pickle`** into segment WAVs, **`python/interpolateGen.py`** does an **`init_noise_level` sweep** in audio-to-audio mode with **`--match-source-length`**, and **`SomaxCorpusWork/pythonScripts/workflow_noise_level_concat.py`** buckets by noise tier and emits **`concatenated/1_noise_level-….wav`**-style mixes. Outputs land under **`Audio/output/…`** with names **`python/output_naming.py`** builds (`sm` small model tag, **`s15`** steps, **`pp`** sampler, timestamps—files like **`wail-augmented-5xstr_sm_swinit_noise_level-0.6_nl0.6_s15_cfg1_pp_d11_*`** when you run the wail rigs).

> **Why:** One mental model beats re-learning each script; chaining the same steps made batch listening comparable across corpora rather than reinventing filenames or folder shapes every week.

Stable Audio pulls **`stabilityai/stable-audio-open-small`** in my traces at **44.1 kHz** with a reported cap near **11.89 s**; my wail clips sit around **~10 s** so **`--match-source-length`** trims generations before concat. On CPU I get benign stderr: **`flash_attn`** optional, **`torch.cuda.amp`** disabled without CUDA, **`clip`** nagging about **`pkg_resources`**.

> **Why:** I cared that outputs line up temporally across segments—I didn’t want the model pad/trunc guesses to spoil A/B-ing noise tiers by length alone.

Below, **Git** hashes are breadcrumbs if you want to bisect—the story is chronological.

---

### Session — April 21, morning (cold start)

I stood the repo up with the Python CLIs **`interpolateGen.py`**, **`sampleReplace.py`**, **`testGen.py`**, **`python/output_naming.py`**, **`setup/downloadModel.py`**, **`setup/downloadModelSmall.py`**, **`requirements.txt`**, plus docs as **`Docs.md`**. I checked in **`2505.08175v3.pdf`** (later renamed **`stableAudioOpenSmall_Paper.pdf`** under **`Documentation/`**). I set **`.gitignore`** so **`Audio/`**, **`*.wav`**, model weights, and secrets stay local, and **`.gitattributes`** for sane line endings.

> **Why:** I needed a reproducible Stable Audio toolbox first; the PDF kept the small-model rationale one click away; ignoring audio/weights avoids slow clones and leaked paths.

**Commands you’d still use:** after a venv, `pip install -r requirements.txt` (later partly superseded by **`pyproject.toml`**), then e.g. `python setup/downloadModelSmall.py` or `python setup/downloadModel.py` with Hugging Face auth.

> **Why:** Download scripts document the HF contract explicitly so I wasn’t reinventing **`from_pretrained`** quirks every reinstall.

*(Git: `622a0cf`)*  

I slipped in an agent-oriented Hugging Face skill under **`.agents/skills/hf-cli/`** (linked from **`.claude/skills/hf-cli`**).

> **Why:** Agents keep asking me to automate Hub pulls—I wanted tooling text co-located with the repo rather than scribbled elsewhere.

*(Git: `2f052e3`)*

---

### Session — April 21 (README and packaging)

I wrote **`README.md`** so cloning is obvious—venv, install, **`setup/downloadModel*.py`**, **`python/sampleReplace.py`**, **`python/interpolateGen.py`**. Examples I still cite:

```bash
python python/sampleReplace.py --prompt "solo violin music" -n 3 --duration 10
python python/sampleReplace.py --indir my_samples --prompt "warm analog pad" --noise-level 0.3
```

> **Why:** Future me forgets invocation order; pasted commands shorten the shame spiral when I return after months.

*(Git: `9563c19`)*  

I formalized **`pyproject.toml`** (`stable-audio-scripts`, **`stable-audio-tools==0.0.19`**, Python ≥3.11), centralized inference in **`python/audio_utils.py`**, and tightened **`python/output_naming.py`** and **`--outdir`** behavior.

> **Why:** Copy-pasting four near-identical loaders was brittle; pinning deps plus one shared naming module kept runs explainable (“same flags → same basename tokens”).

*(Git: `704cf9b`, `43cd100`)*  

Over Cursor someone asked how **`generate_diffusion_cond`** works inside **`python/testGen.py`** (transcript **`6788a62e-b6df-467e-92a6-a1da34378716`**).

> **Why:** I treat **`testGen.py`** as a telescope into the sampler—walking it beat reading raw library source cold.

---

### Session — April 23 (folder batch interpolation)

I taught **`python/interpolateGen.py`** to accept **`--init-audio`** as either a single file **or a folder**, sweeping **`init_noise_level`** across every clip without reloading weights between inputs.

> **Why:** My Somax-derived folders routinely hold tens of shorts—folder mode turned “research afternoon” into one load, many sweeps, less thrash waiting on Torch init.

*(Git: `effa002`)*  

Example I still shout into the void:

```bash
python python/interpolateGen.py --init-audio my_samples/ --prompt "dreamy pads" \
  --param init_noise_level --start 0.1 --end 0.9 -n 5 --match-source-length
```

> **Why:** This snippet is how I audition “how chaotic can this corpus get?” without rewriting Python each time.

---

### Session — April 29 (segments without the model)

I added **`python/segment_audio.py`** for chopping **outside** Somax—equal-duration cores capped by **`--max-seconds`** (default aligns with Stable Audio horizons), optional **`--overlap-ms`**:

```bash
python python/segment_audio.py long_take.wav --max-seconds 11 --output-dir segments/
```

> **Why:** Some sources never touch Somax2; I still needed clip lengths the small model happily ingests instead of babysitting trims by hand.

**Audio path:** arbitrary **`long_take.wav`**, outputs beside the file or **`segments/`**.

*(Git: `10b7feb`)*  

---

### Session — April 29 (Somax tooling + first shell pipelines)

I moved Python under **`python/`**, installers **`setup/`**, **`Docs.md` → `Documentation/Docs.md`**, and ported **SomaxCorpusWork** (`segment_corpus.py`, `concat_segments.py`, `organize_by_noise_level.py`, `workflow_*`, corpus PDF/PDF/maxpat stash).

> **Why:** The Somax-derived automation deserved first-class citizenship next to Stable Audio—not a dangling folder—and flat **`python/`** keeps imports sane for shell wrappers.

I authored **`scripts/alto_recorder_pipeline.sh`**:

**Inputs:** **`SomaxCorpusWork/Corpora/MultiCorpus2_alto-rec/alto_recorder_UNT.wav`** + **`alto_recorder_UNT.pickle`** → **`alto_recorder_UNTSegments/`**  

> **Why:** That alto recorder corpus was my first guinea pig stitching Somax segmentation to Stable Audio resynthesis—I needed an end-to-end proof before scaling to bigger choirs/noise.

**Prompts:** **`scripts/alto_recorder_prompts.json`** (eight lines: alto recorder warmth, airy winds, dub growl, distressed countertenor wail, dry jazz drums, techno kit, fiddle, metal barrage).

> **Why:** I wanted a terse prompt palette mirroring sonic directions I audition for that instrument—dense enough for contrast, short enough that JSON stayed human-editable.

**Generation:** **`interpolateGen.py`** **`--start 0.6` `--end 0.9`**, **`-n 2`**, **`--steps 2`**, **`--match-source-length`**, tying **`SWEEP_N`** to **`workflow_noise_level_concat.py --noise-levels`**  

> **Why:** I prioritized quick smoke tests (**`steps 2`, two noise taps**) early; aligning **`SWEEP_N`** avoids silent mismatches (“where’s the tenth folder?” dramas).

**Outputs:** **`Audio/output/prompt##_sweep_init_noise_level_<timestamp>/`** with **`concatenated/`**.

```bash
bash scripts/alto_recorder_pipeline.sh
```

Later **`scripts/alto_recorder_pipeline_15step.sh`** bumps **`interpolateGen.py`** to **`--steps 15`**.

> **Why:** Once smoke tests behaved, richer diffusion steps tightened textures without rewriting the choreography.

*(Git: `f9ccbc3`, **`Documentation/`** stabilized `acb269a`, alto variant `8322e83`)*  

I drafted **`Documentation/shell_scripts.md`**, **`Documentation/setup.md`**, **`Documentation/noise_level_vs_steps.md`**.

> **Why:** I kept confusing **diffusion steps** with **noise levels** verbally—writing the distinction down reduced self-sabotage when tuning envelopes.

---

### Session — April 29 (silence remover)

Someone (via Cursor **`dec890f7-…`**) requested preprocessing stripping silence longer than **`--min-silence`** (default **1 s**). **`SomaxCorpusWork/pythonScripts/remove_silence.py`** landed—stdlib WAV slicing, thresholds, directories.

> **Why:** Long dead air in Somax exports wasted segment budget and exaggerated “model invents tails” artefacts—I wanted corpuses lean before pickles drive segmentation.

```bash
python3 SomaxCorpusWork/pythonScripts/remove_silence.py \
  SomaxCorpusWork/Corpora/MultiCorpus2_alto-rec/alto_recorder_UNT.wav \
  SomaxCorpusWork/Corpora/MultiCorpus2_alto-rec/alto_recorder_UNT_no_silence.wav \
  --min-silence 1.0
```

*(Git: `0a217ab`)*

---

### Session — April 30 (concat edge cases, PC playbook, heavy GEC rigs)

**`SomaxCorpusWork/pythonScripts/concat_segments.py`** now sorts lexically if **`segment*.wav`** misses.

> **Why:** Interpolation renames scrambled the simple glob—falling back to deterministic sorting rescues overnight renders instead of silently wrong stitch order.

I wrote **`Documentation/pc_setup.md`** after hashing out Dropbox/GitHub splits: repo on Git, **`Audio/`** on Dropbox/Git Bash **`bash`** on Windows overnight.

> **Why:** My Mac churns drafts; my PC brute-forces batches—I needed a playbook so both machines agree without Sync conflicts eating half-written WAV directories.

**`scripts/gecVoxFull_pipeline_15step.sh`** targets **`SomaxCorpusWork/Corpora/MutliCorpus3_gecVox/gecVoxFull_no_silence.{wav,pickle}` → `gecVoxFull_no_silenceSegments/`**, **`scripts/gecVoxFull_prompts.json`** (autotune, airy orchestral, dub bass, male wail, jazz drums, techno kit, fiddle, extreme metal), **`MAX_SEGMENTS=40`**, **`SWEEP_N=10`** ( **`init_noise_level` 0.3→0.9**):

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

> **Why:** GEC vox corpus needed more granularity than alto smoke tests—ten noise tiers let me audition “barely recognizable” versus “barely tethered,” and wider **0.3** start leaned into drama earlier.

Path fix **`90bfa96`**; mid-run tweaks ensuring **`workflow_noise_level_concat.py --noise-levels`** matches **`-n`** (transcript **`1bd86662-…`**).

> **Why:** When counts drift, step three invents heartbreaking empty folders—you caught that mismatch live; aligning flags was cheaper than hallucinating QA patience.

**`scripts/gecVoxFullSMALL_pipeline_15step.sh`** points at **`gecVoxFull_no_silenceSegmentsSmall`** while STEP 1 **`AUDIO_FILE` lines stay commented—as checked in I treat it as “pre-segmented small folder only.”**

> **Why:** I sometimes shrink segment sets offline; flipping comments every time annoyed me enough to commit a deliberately “continuation-only” harness.

*(Git core: `0f5e769`)*

---

### Session — April 30 (pad everything to one reference duration)

Butterfly-sweep segments needed padding to **`gecVoxFull_no_silence.wav`** length—**`SomaxCorpusWork/pythonScripts/pad_to_reference_duration.py`**.

> **Why:** Downstream Stable Audio listens for uniform timing; drifting lengths meant crossfades lied—padding/trunc anchors kept comparisons honest.

```bash
python SomaxCorpusWork/pythonScripts/pad_to_reference_duration.py \
  SomaxCorpusWork/Corpora/MutliCorpus3_gecVox/gecVoxFull_no_silence.wav \
  SomaxCorpusWork/Corpora/MutliCorpus3_gecVox/1-8_butterfly-sweep_39segs_silencepadded \
  --outdir SomaxCorpusWork/Corpora/MutliCorpus3_gecVox/padded_out
```

*(Git: `b6a59c7`)*

---

### Session — April 30 (human ops)

We chatted about laptop lids freezing bash (**`ce30ed9e-…`**)—no repo diff. Somax region filter questions floated in **`06f1d909-…`**.

> **Why:** Logistics and MaxMSP literacy still gate whether these scripts survive real life—even when no LOC moved.

---

### Session — May 8 (document `segment_audio`)

Documented **`python/segment_audio.py`** inside **`Documentation/Docs.md`** after you wondered if that helper was written down (**`95cc9eb5-…`**).

> **Why:** If only I memorized argparse—Docs prevent “wait, wasn’t there a splitter?” archaeology.

*(Git: `f9639c1`)*

---

### Session — May 8 (wail rigs + runs I logged)

Committed **`scripts/WailStretchSMALL_pipeline_curated.sh`** and **`scripts/WailStretchSMALL_pipeline.sh`**.

**Corpus notion:** **`SomaxCorpusWork/Corpora/MultiCorpus4_wail/Segments_wail_augmented_5xStretched`** (clips like **`wail_augmented_5xStretched_seg001.wav`**)

> **Why:** That stretched wail corpus is my stress-test for extremes—textures already pushed so Stable Audio deviations read clearly.

**Prompt libraries:**

- **`scripts/stable_audio_prompts_curated.json`** — forty-three long genre/SFX hybrids (thrash to spa pads to smartphone ringtones).  
> **Why:** Wide prompt net stress-tests sonic diversity while keeping Stable Audio specificity high—listening fatigue told me terse prompts wasted compute.
- **`scripts/wailStretch_prompts.json`** / **`wailStretch_prompts_2.json`** — seven short lines each; **`_2`** suffixes **`300 BPM`** everywhere.  

> **Why:** I wanted apples-to-apples “tempo tag” experiments without rewriting prose—seven prompts stays finishable overnight.

Curated **`PROMPT_FILE="scripts/stable_audio_prompts_curated.json"`**; alternate script binds **`wailStretch_prompts_2.json`** and nests outputs **`Audio/output/wailStretch300BPMtest/prompt##_…`**.

> **Why:** Curated saturation vs tight “wail BPM” cohort deserve separate trees so listeners never confuse audience intent.

**Sweep knobs:** **`init_noise_level`** **0.6→0.9**, **`SWEEP_N=3`**, **`--steps 15`**, **`pingpong`**, **`--match-source-length`**.

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

> **Why:** Three stops keeps render time humane while spanning “still wail-ish” versus “barely tethered”; fifteen steps reins in grain without month-long grids.

Because **`bash`** runs **`set -u`**, I added **`SKIP_SEGMENT_STEP=1`** for pre-segmented dirs.

```bash
SKIP_SEGMENT_STEP=1 bash scripts/WailStretchSMALL_pipeline_curated.sh
SKIP_SEGMENT_STEP=1 bash scripts/WailStretchSMALL_pipeline.sh
```

> **Why:** Re-segmentation is costly and Somax fiddly—being able to hot-swap prompts without touching pickles saved entire evenings.

The **`AUDIO_FILE: unbound variable`** chase produced safer guards (**`b6ff13ee-…`**).

> **Why:** Commented placeholders + **`set -u`** is lethal—I'd rather crash with instructions than phantom expansions wasting GPU hours mid-loop.

**Terminal souvenirs:** **`terminals/1.txt`** exited **0** after **41** curated prompts (**`20260508_182717`** tree; **`~9.99 s`** segments → **`~29.956 s`** concats). **`terminals/8.txt`** exited **0** after **7** prompts under **`wailStretch300BPMtest`** (**`20260508_185647`**).

> **Why:** Concrete stamps plus wave counts vindicate narration—knowing durations matched meant I wasn't gaslighting myself about cropping.

Prompt craft thread **`f8786ab1-…`** tied prose to **`Documentation/stableAudioOpenSmall_Paper.pdf`**.

> **Why:** When prompts drift from model strengths, grids feel random—anchoring language to the ARC/small-model story kept experiments intellectually tethered.

*(Git: `61c1d6b`)*

---

### Session — meta (this document)

Merged git + transcripts + terminals into **`Documentation/project_evolution_log.md`** (**`61f6b832-…`**) and iterated here.

> **Why:** Institutional memory dissipates—I’d rather sentimentalise process in prose than reconstruct intent from orphaned JSON.

---

## Quick map — where binaries and corpora plug in


| Script | Canonical inputs | Prompt list | Outputs |
| --- | --- | --- | --- |
| **`scripts/alto_recorder_pipeline*.sh`** | **`MultiCorpus2_alto-rec/alto_recorder_UNT.{wav,pickle}` → `alto_recorder_UNTSegments/`** (**`MAX_SEGMENTS`** trims) | **`scripts/alto_recorder_prompts.json`** | **`Audio/output/prompt##_sweep_init_noise_level_<stamp>/`** + **`concatenated/`** |
| **`scripts/gecVoxFull_pipeline_15step.sh`** | **`MutliCorpus3_gecVox/gecVoxFull_no_silence.{wav,pickle}` → `…Segments/`** (first **40** default) | **`scripts/gecVoxFull_prompts.json`** | same pattern (**`SWEEP_N=10`, noise 0.3–0.9**) |
| **`scripts/WailStretchSMALL_pipeline_curated.sh`** | **`Segments_wail_augmented_5xStretched`** (**`SKIP_SEGMENT_STEP=1`** friendly) | **`stable_audio_prompts_curated.json`** | flat **`Audio/output/prompt##_…`** |
| **`scripts/WailStretchSMALL_pipeline.sh`** | same corpus dir notion | **`wailStretch_prompts_2.json`** *(as committed)* | nested **`Audio/output/wailStretch300BPMtest/`** |

> **Why:** This table exists so you can skim “which JSON lights which fuse” faster than deciphering duplicated bash skeletons—I’m allergic to flipping four scripts mentally while listening.

---

## Keeping this conversational log honest

When you rerun something material, jot the echoed **`TIMESTAMP`**, **`PROMPT_FILE`**, **`MAX_SEGMENTS`**, **`SWEEP_N`**, and whether stderr showed **`flash_attn`** / CUDA issues—we mostly log **routing** (`python/interpolateGen.py …`), not WAV blobs themselves.

> **Why:** The sounds age; the knobs should remain inspectable—I’d rather scribble timestamps than audition mystery folders labeled “final_final_v3.”
