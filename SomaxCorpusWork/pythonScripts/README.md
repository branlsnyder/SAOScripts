# Somax2 Corpus Segmentation Tools

Python utilities for splitting, concatenating, and organizing audio segments from [Somax2](https://music-interaction-music.music.ircam.fr/Somax2) corpora. No external dependencies required — everything uses the Python standard library.

Scripts are split into two categories:

- **Single tasks** — do one atomic operation (split, concatenate, or organize).
- **Workflows** (`workflow_` prefix) — chain multiple tasks into an end-to-end pipeline.

---

## Single Tasks

### `segment_corpus.py` — Split a corpus into segments

Reads a Somax2 `.pickle` corpus file and its corresponding WAV file, then extracts each event/segment as an individual WAV file. The first and last segments are extended so the output covers the full duration of the original audio exactly.

Uses a custom unpickler that stubs out Somax2 classes, so Somax2 does not need to be installed.

```
python segment_corpus.py <audio_file> <pickle_file> [output_folder]
```

| Argument | Description |
|---|---|
| `audio_file` | Path to the source WAV file |
| `pickle_file` | Path to the Somax2 `.pickle` corpus file |
| `output_folder` | *(Optional)* Output folder. Defaults to `<corpus_name>Segments` |

**Example:**
```bash
python segment_corpus.py Fabbrizio2c.wav Fabbrizio2c.pickle
# -> Fabbrizio2cSegments/segment_000.wav, segment_001.wav, ..., segment_234.wav
```

---

### `concat_segments.py` — Concatenate segments into one file

The reverse of `segment_corpus.py`. Takes a folder of `segment_NNN.wav` files and concatenates them in numeric order into a single WAV file. Filenames can contain extra text after the index (e.g. `segment_007_processed.wav`) — only the `segment_NNN` prefix is used for sorting.

```
python concat_segments.py <segments_folder> [output_file]
```

| Argument | Description |
|---|---|
| `segments_folder` | Folder containing `segment_NNN*.wav` files |
| `output_file` | *(Optional)* Output WAV path. Defaults to `<folder_name>.wav` |

**Example:**
```bash
python concat_segments.py Fabbrizio2cSegments Fabbrizio2c_rebuilt.wav
```

---

### `organize_by_noise_level.py` — Sort files into noise-level folders

Moves WAV files from a flat directory into subfolders grouped by their `noise_level-X.XXXX` identifier (parsed from the filename). Designed for output from multi-corpus Somax2 generation runs.

```
python organize_by_noise_level.py
```

Operates on the `multiCorpus1_joelle2digital/` directory relative to the script. A file like:
```
segment-016_sm_swinit_noise_level-0.7154_nl0.7154_s8_cfg1_pp_d11_030_20260423_102110.wav
```
is moved into `noise_level-0.7154/`.

---

## Workflows

### `workflow_batch_concat.py` — Batch-concatenate noise-level folders

After files have been organized into `noise_level-X.XXXX/` subfolders (by `organize_by_noise_level.py`), this script concatenates each subfolder's segments into a single WAV file. Output files are placed in a `concatenated/` directory with zero-padded index prefixes so they sort by ascending noise level.

Imports `concat_segments` directly for the concatenation logic.

```
python workflow_batch_concat.py
```

Operates on the `multiCorpus1_joelle2digital/` directory relative to the script. Produces output like:
```
multiCorpus1_joelle2digital/concatenated/
  01_noise_level-0.0000.wav
  02_noise_level-0.0256.wav
  ...
  40_noise_level-1.0000.wav
```

---

### `workflow_noise_level_concat.py` — Organize and concatenate in one step

A combined, generalized version of `organize_by_noise_level.py` and `workflow_batch_concat.py`. Given any flat directory of WAV files with `noise_level-X.XXXX` in their names, it:

1. Groups files by noise level
2. Moves each group into its own subfolder
3. Concatenates every subfolder's segments into a single WAV

```
python workflow_noise_level_concat.py <input_dir> [--noise-levels N]
```

| Argument | Description |
|---|---|
| `input_dir` | Flat directory containing the segment WAV files |
| `--noise-levels N` | *(Optional)* Expected number of unique noise levels (verified, not enforced) |

**Example:**
```bash
python workflow_noise_level_concat.py multiCorpus1_joelle2digital --noise-levels 40
```

---

## Typical Workflow

```
1.  Build a corpus in Somax2 -> produces audio.wav + corpus.pickle

2.  Split into segments:
      python segment_corpus.py audio.wav corpus.pickle

3.  Process individual segments (external tools, effects, etc.)

4.  Reassemble:
      python concat_segments.py AudioSegments/ output.wav
```

For multi-noise-level generation runs, use `workflow_noise_level_concat.py` to organize and concatenate everything in one command.
