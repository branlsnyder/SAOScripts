# Noise Level vs Steps: How They Influence Output

Both **steps** and **noise-level** (`init_noise_level`) shape the final audio, but they operate on fundamentally different axes of the generation process.

## What each one controls

| | **Steps** | **Noise Level** |
|---|---|---|
| **What it governs** | How many iterative denoising passes the model performs | How much noise is mixed into the input audio's latent representation before denoising begins |
| **Applies to** | Both text-to-audio and audio-to-audio | Audio-to-audio only (ignored without `--init-audio`) |
| **Metaphor** | How carefully the painter works | How much of the original sketch is erased before the painter starts |

## How they influence the output

### Noise level — *degree of departure from the source*

Noise level controls the **balance between preservation and regeneration**. It answers: "How much of the original audio's structure should survive?"

| Range | Effect |
|---|---|
| 0.1–0.2 | Very close to original — subtle restyling, same rhythm/pitch/envelope |
| 0.3–0.5 | Moderate departure — new textures but recognizable structure |
| 0.6–0.8 | Substantial regeneration — only a loose structural echo of the input remains |

At low noise levels, the model has little room to deviate — the original audio dominates. At high noise levels, the input is nearly obliterated by noise and the model essentially generates fresh audio loosely guided by the prompt and whatever faint structural residue survives.

### Steps — *quality and refinement of the generation*

Steps controls the **fidelity of whatever the model generates**, regardless of how it got there. It answers: "How much time does the model spend refining its output?"

| Range | Effect |
|---|---|
| 2–4 | Fast, rough, potentially noisy/artifact-prone |
| 6–10 | Practical sweet spot (default 8) — good quality, fast |
| 15–30 | More refined detail, cleaner textures |
| 30–50+ | Diminishing returns — marginal improvement, linear time increase |

## Key distinction

- **Noise level** determines **what** the model generates — how much it preserves vs. invents.
- **Steps** determines **how well** the model generates it — how polished the result is.

A concrete example: if you set `noise-level=0.2` and `steps=50`, you'll get a very faithful, highly refined version of your input. If you set `noise-level=0.8` and `steps=4`, you'll get something wildly different from your input *and* rough/undercooked. These two parameters are orthogonal — you can mix and match them freely.

## Interaction between them

They don't directly depend on each other, but there's a practical nuance: **high noise levels benefit more from higher step counts**. When the model has to reconstruct a lot (high noise), giving it more denoising passes helps it produce cleaner, more coherent output. Conversely, at very low noise levels, the model is just lightly touching up existing audio, so fewer steps are often sufficient.
