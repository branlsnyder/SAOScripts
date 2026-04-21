"""
Centralized output file naming and directory management.

All audio outputs go to Audio/output/ with a standardized naming scheme:

    {base}_{flags}_{timestamp}.wav

- base: input filename stem (audio-to-audio) or first 7 chars of prompt (text-to-audio)
- flags: abbreviated generation parameters
- timestamp: YYYYMMDD_HHMMSS to prevent overwrites
"""

import os
import re
from datetime import datetime

OUTPUT_DIR = os.path.join("Audio", "output")

SAMPLER_ABBREV = {
    "pingpong": "pp",
    "dpmpp-3m-sde": "dpm3m",
    "dpmpp-2m-sde": "dpm2m",
    "k-heun": "khn",
    "k-lms": "klms",
    "k-dpmpp-2s-ancestral": "kdpm2s",
}

MODEL_ABBREV = {
    "stable-audio-open-small": "sm",
    "stable-audio-open": "lg",
}


def _sanitize(s: str, max_len: int = 20) -> str:
    """Lowercase, collapse non-alphanum to hyphens, strip edges, truncate."""
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s[:max_len]


def _fmt(value) -> str:
    """Format a number compactly: drop trailing zeros, cap at 4 significant digits."""
    if isinstance(value, int):
        return str(value)
    s = f"{value:.4g}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def build_output_path(
    *,
    prompt: str = None,
    input_filename: str = None,
    steps: int = None,
    cfg_scale: float = None,
    seed: int = None,
    noise_level: float = None,
    sampler_type: str = None,
    duration: float = None,
    model: str = None,
    sweep_param: str = None,
    sweep_value=None,
    index: int = None,
    ext: str = ".wav",
) -> str:
    """
    Build a standardized output file path under Audio/output/.

    For audio-to-audio, pass input_filename (the original file's basename).
    For text-to-audio, pass prompt (first 7 chars are used).
    For sweeps, pass sweep_param and sweep_value.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # --- base identifier ---
    if input_filename:
        stem = os.path.splitext(input_filename)[0]
        base = _sanitize(stem)
    elif prompt:
        base = _sanitize(prompt[:7])
    else:
        base = "out"

    # --- flag parts ---
    parts = []

    if model:
        parts.append(MODEL_ABBREV.get(model, model[:4]))

    if sweep_param and sweep_value is not None:
        parts.append(f"sw{sweep_param}-{_fmt(sweep_value)}")

    if noise_level is not None:
        parts.append(f"nl{_fmt(noise_level)}")

    if steps is not None:
        parts.append(f"s{steps}")

    if cfg_scale is not None:
        parts.append(f"cfg{_fmt(cfg_scale)}")

    if seed is not None and seed != -1:
        parts.append(f"sd{seed}")

    if sampler_type:
        parts.append(SAMPLER_ABBREV.get(sampler_type, _sanitize(sampler_type, 6)))

    if duration is not None:
        parts.append(f"d{_fmt(duration)}")

    if index is not None:
        parts.append(f"{index:03d}")

    flags = "_".join(parts)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    filename = f"{base}_{flags}_{timestamp}{ext}" if flags else f"{base}_{timestamp}{ext}"
    return os.path.join(OUTPUT_DIR, filename)
