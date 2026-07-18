"""
Segment an audio file into equal-length parts, each under a given maximum duration.

Usage:
    python segment_audio.py input.wav
    python segment_audio.py input.wav --max-seconds 11 --output-dir segments
    python3 python/segment_audio.py "/Users/brandonwoosnyder/Documents/04_Repos/CREATIVE WORK REPOS/StableAudioWorkspace/SomaxCorpusWork/Corpora/MutilCorpus6_KAACMixtapes/Gee/Gee - Girls Generation.wav" --max-seconds 11 --output-dir "/Users/brandonwoosnyder/Documents/04_Repos/CREATIVE WORK REPOS/StableAudioWorkspace/SomaxCorpusWork/Corpora/MutilCorpus6_KAACMixtapes/Gee/gee_segments"
"""

import argparse
import math
from datetime import datetime
from pathlib import Path

import numpy as np
import soundfile as sf


def segment_audio(
    input_path: str,
    max_seconds: float = 11.0,
    overlap_ms: float = 0.0,
    output_dir: str | None = None,
) -> list[Path]:
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"File not found: {input_path}")

    data, sample_rate = sf.read(str(input_path))
    if data.ndim == 1:
        data = data[:, np.newaxis]
    total_samples = data.shape[0]
    total_duration = total_samples / sample_rate
    channels = data.shape[1]

    overlap_samples = int((overlap_ms / 1000.0) * sample_rate)

    effective_max = max_seconds - 2 * (overlap_ms / 1000.0)
    if effective_max <= 0:
        raise ValueError(
            f"Overlap ({overlap_ms}ms x2 = {2*overlap_ms}ms) exceeds "
            f"max segment duration ({max_seconds}s). Reduce overlap or increase --max-seconds."
        )

    num_segments = math.ceil(total_duration / effective_max)
    segment_duration = total_duration / num_segments
    segment_samples = int(segment_duration * sample_rate)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if output_dir is None:
        out = input_path.parent / f"{input_path.stem}_segments_{timestamp}"
    else:
        out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    if overlap_ms > 0:
        print(f"Overlap: {overlap_ms}ms ({overlap_samples} samples) on each side")

    saved: list[Path] = []
    for i in range(num_segments):
        core_start = i * segment_samples
        core_end = min(core_start + segment_samples, total_samples)

        read_start = core_start - overlap_samples
        read_end = core_end + overlap_samples

        pad_before = max(0, -read_start)
        pad_after = max(0, read_end - total_samples)

        actual_start = max(0, read_start)
        actual_end = min(total_samples, read_end)
        chunk = data[actual_start:actual_end]

        if pad_before > 0 or pad_after > 0:
            chunk = np.pad(
                chunk,
                ((pad_before, pad_after), (0, 0)),
                mode="constant",
            )

        dest = out / f"{input_path.stem}_seg{i+1:03d}{input_path.suffix}"
        sf.write(str(dest), chunk, sample_rate)
        saved.append(dest)

        chunk_dur = chunk.shape[0] / sample_rate
        core_dur = (core_end - core_start) / sample_rate
        label = f"{chunk_dur:.3f}s" if overlap_ms == 0 else f"{chunk_dur:.3f}s, core {core_dur:.3f}s"
        print(f"  [{i+1}/{num_segments}] {dest.name}  ({label})")

    print(
        f"\nDone — {num_segments} segments of ~{segment_duration:.3f}s core "
        f"(all under {max_seconds}s with overlap) saved to {out}"
    )
    return saved


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Split an audio file into equal parts, each under a maximum duration."
    )
    parser.add_argument("input", help="Path to the input audio file")
    parser.add_argument(
        "--max-seconds",
        type=float,
        default=11.0,
        help="Maximum duration per segment in seconds (default: 11)",
    )
    parser.add_argument(
        "--overlap-ms",
        type=float,
        default=0.0,
        help="Overlap in milliseconds added to each side of every segment for crossfading (default: 0)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for output segments (default: <input_stem>_segments/)",
    )
    args = parser.parse_args()
    segment_audio(args.input, args.max_seconds, args.overlap_ms, args.output_dir)
