#!/usr/bin/env python3
"""
Concatenate a folder of WAV files into a single audio file.

Usage:
    python concat_segments.py <segments_folder> [output_file]

Arguments:
    segments_folder   Path to the folder containing WAV files to concatenate
    output_file       (Optional) Output WAV path. Defaults to <folder_name>.wav

Files named segment_NNN or segment-NNN are sorted by their numeric index.
Any other WAV filenames are sorted alphabetically.
Files with mismatched sample rates or channel counts are resampled/remixed
to match the first file's format.
"""

import argparse
import glob
import os
import re
import sys

import numpy as np
import soundfile as sf


def find_segments(folder: str) -> list[str]:
    """Find and sort segment WAV files by their numeric index, falling back to
    alphabetical sorting for arbitrary WAV filenames."""
    pattern = os.path.join(folder, "segment_*.wav")
    files = glob.glob(pattern)
    if not files:
        pattern = os.path.join(folder, "segment-*.wav")
        files = glob.glob(pattern)

    if files:
        def sort_key(path: str) -> int:
            match = re.search(r"segment[-_](\d+)", os.path.basename(path))
            return int(match.group(1)) if match else 0
        files.sort(key=sort_key)
    else:
        files = sorted(glob.glob(os.path.join(folder, "*.wav")))

    if not files:
        print(f"Error: no .wav files found in {folder}", file=sys.stderr)
        sys.exit(1)

    return files


def _match_channels(data: np.ndarray, target_channels: int) -> np.ndarray:
    """Convert mono <-> stereo to match the target channel count."""
    if data.ndim == 1:
        src_channels = 1
    else:
        src_channels = data.shape[1]

    if src_channels == target_channels:
        return data

    if src_channels == 1 and target_channels == 2:
        mono = data if data.ndim == 1 else data[:, 0]
        return np.column_stack([mono, mono])

    if src_channels == 2 and target_channels == 1:
        return data.mean(axis=1)

    print(
        f"Warning: cannot convert {src_channels}ch -> {target_channels}ch, "
        f"taking first {target_channels} channel(s)",
        file=sys.stderr,
    )
    if data.ndim == 1:
        return data
    return data[:, :target_channels]


def concat_segments(segments_folder: str, output_file: str) -> None:
    segments = find_segments(segments_folder)
    print(f"Found {len(segments)} segments in {segments_folder}/")

    ref_info = sf.info(segments[0])
    sr = ref_info.samplerate
    n_channels = ref_info.channels

    print(f"Format: SR={sr}  Channels={n_channels}  (from first file)")
    print(f"Output: {output_file}")
    print()

    chunks: list[np.ndarray] = []
    total_frames = 0

    for path in segments:
        data, file_sr = sf.read(path, dtype="float64", always_2d=(n_channels > 1))

        if file_sr != sr:
            try:
                import soxr
                data = soxr.resample(data, file_sr, sr)
            except ImportError:
                ratio = sr / file_sr
                n_out = int(len(data) * ratio)
                indices = (np.arange(n_out) / ratio).astype(int)
                indices = np.clip(indices, 0, len(data) - 1)
                data = data[indices]
            print(f"  (resampled {file_sr} -> {sr})")

        data = _match_channels(data, n_channels)
        frames = len(data)
        chunks.append(data)
        total_frames += frames

        dur = frames / sr
        print(f"  {os.path.basename(path):>50s}  {frames:>8d} frames  ({dur:.3f}s)")

    output = np.concatenate(chunks)
    sf.write(output_file, output, sr)

    total_duration = total_frames / sr
    print()
    print(f"Total: {total_frames} frames  ({total_duration:.3f}s)")
    print(f"Written to {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Concatenate WAV files into a single audio file."
    )
    parser.add_argument("segments_folder", help="Folder containing WAV files to concatenate")
    parser.add_argument(
        "output_file",
        nargs="?",
        default=None,
        help="Output WAV path (default: <folder_name>.wav)",
    )
    args = parser.parse_args()

    if not os.path.isdir(args.segments_folder):
        print(f"Error: folder not found: {args.segments_folder}", file=sys.stderr)
        sys.exit(1)

    if args.output_file is None:
        folder_name = os.path.basename(os.path.normpath(args.segments_folder))
        args.output_file = f"{folder_name}.wav"

    concat_segments(args.segments_folder, args.output_file)


if __name__ == "__main__":
    main()
