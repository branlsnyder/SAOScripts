#!/usr/bin/env python3
"""
Organize segment WAV files by noise level and concatenate each group.

Given a flat directory of WAV files whose names contain a noise_level-X.XXXX
token, this script:

  1. Groups files by their noise_level ID.
  2. Moves each group into its own subfolder  (noise_level-X.XXXX/).
  3. Concatenates every subfolder's segments into a single WAV file,
     written to a "concatenated/" output directory with zero-padded
     index prefixes so files sort by ascending noise level.

Usage:
    python noise_level_concat.py <input_dir> [--noise-levels N]

Arguments:
    input_dir          Flat folder of segment WAV files.
    --noise-levels N   Expected number of unique noise levels (optional).
                       If provided, the script verifies the count matches.

Everything else (segment count per group, total file count, index padding
width) is detected automatically.
"""

import argparse
import glob
import math
import os
import re
import shutil
import sys
import wave


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOISE_LEVEL_RE = re.compile(r"(noise_level-[\d.]+)_")


def parse_noise_value(nl_id: str) -> float:
    """Extract the float value from a string like 'noise_level-0.7154'."""
    return float(nl_id.split("-", 1)[1])


def find_segments(folder: str) -> list[str]:
    """Return all WAV files in *folder*, sorted by leading segment index."""
    files = glob.glob(os.path.join(folder, "*.wav"))
    if not files:
        print(f"Error: no .wav files found in {folder}", file=sys.stderr)
        sys.exit(1)

    def sort_key(path: str) -> tuple:
        base = os.path.basename(path)
        m = re.search(r"segment[-_](\d+)", base)
        if m:
            return (0, int(m.group(1)), "")
        m = re.search(r"(\d{8}_\d{6})(?:\.wav)?$", base)
        if m:
            return (0, 0, m.group(1))
        return (1, 0, base)

    files.sort(key=sort_key)
    return files


def concat_wav(segments: list[str], output_file: str) -> None:
    """Concatenate a list of WAV paths into a single output WAV."""
    with wave.open(segments[0], "rb") as first:
        sr = first.getframerate()
        n_channels = first.getnchannels()
        sampwidth = first.getsampwidth()

    total_frames = 0
    with wave.open(output_file, "wb") as wav_out:
        wav_out.setnchannels(n_channels)
        wav_out.setsampwidth(sampwidth)
        wav_out.setframerate(sr)

        for path in segments:
            with wave.open(path, "rb") as seg:
                if (seg.getframerate() != sr
                        or seg.getnchannels() != n_channels
                        or seg.getsampwidth() != sampwidth):
                    print(
                        f"Error: {os.path.basename(path)} format mismatch "
                        f"(SR={seg.getframerate()}, Ch={seg.getnchannels()}, "
                        f"Bits={seg.getsampwidth() * 8})",
                        file=sys.stderr,
                    )
                    sys.exit(1)
                frames = seg.getnframes()
                wav_out.writeframes(seg.readframes(frames))
                total_frames += frames

    duration = total_frames / sr
    print(f"    {len(segments)} segments  |  {total_frames} frames  |  {duration:.3f}s")


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def group_by_noise_level(input_dir: str) -> dict[str, list[str]]:
    """Return {noise_level_id: [filename, ...]} for every WAV in input_dir."""
    wav_files = sorted(f for f in os.listdir(input_dir) if f.endswith(".wav"))
    if not wav_files:
        print(f"Error: no .wav files in {input_dir}", file=sys.stderr)
        sys.exit(1)

    groups: dict[str, list[str]] = {}
    unmatched: list[str] = []

    for fname in wav_files:
        m = NOISE_LEVEL_RE.search(fname)
        if m:
            groups.setdefault(m.group(1), []).append(fname)
        else:
            unmatched.append(fname)

    if unmatched:
        print(f"Warning: {len(unmatched)} file(s) did not match the "
              f"noise_level pattern and will be skipped.")

    return groups


def organize_into_subfolders(input_dir: str,
                             groups: dict[str, list[str]]) -> list[tuple[float, str]]:
    """Move files into per-noise-level subfolders. Returns sorted (value, id) list."""
    sorted_ids = sorted(groups, key=lambda k: parse_noise_value(k))
    result = []

    for nl_id in sorted_ids:
        subfolder = os.path.join(input_dir, nl_id)
        os.makedirs(subfolder, exist_ok=True)
        for fname in sorted(groups[nl_id]):
            src = os.path.join(input_dir, fname)
            dst = os.path.join(subfolder, fname)
            if os.path.exists(src):
                shutil.move(src, dst)
        result.append((parse_noise_value(nl_id), nl_id))

    return result


def concatenate_all(input_dir: str,
                    sorted_levels: list[tuple[float, str]]) -> None:
    """Concatenate each subfolder and write indexed output files."""
    output_dir = os.path.join(input_dir, "concatenated")
    os.makedirs(output_dir, exist_ok=True)

    n = len(sorted_levels)
    pad = len(str(n))

    print(f"\nConcatenating {n} noise-level folders -> {output_dir}/\n")

    for idx, (nl_val, nl_id) in enumerate(sorted_levels, start=1):
        folder_path = os.path.join(input_dir, nl_id)
        segments = find_segments(folder_path)
        out_name = f"{idx:0{pad}d}_{nl_id}.wav"
        out_path = os.path.join(output_dir, out_name)

        print(f"  [{idx:0{pad}d}/{n}]  {nl_id}  ->  {out_name}")
        concat_wav(segments, out_path)

    print(f"\nDone. {n} concatenated files written to:\n  {output_dir}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Organize segment WAVs by noise level, then concatenate each group.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "input_dir",
        help="Flat directory containing the segment WAV files.",
    )
    parser.add_argument(
        "--noise-levels", "-n",
        type=int,
        default=None,
        metavar="N",
        help="Expected number of unique noise levels (verified, not enforced).",
    )
    args = parser.parse_args()

    input_dir = os.path.abspath(args.input_dir)
    if not os.path.isdir(input_dir):
        print(f"Error: directory not found: {input_dir}", file=sys.stderr)
        sys.exit(1)

    # --- Step 1: group ---
    groups = group_by_noise_level(input_dir)
    n_levels = len(groups)
    seg_counts = sorted(set(len(v) for v in groups.values()))
    total_files = sum(len(v) for v in groups.values())

    print(f"Input:          {input_dir}")
    print(f"Total WAVs:     {total_files}")
    print(f"Noise levels:   {n_levels}")
    print(f"Segments/level: {', '.join(str(c) for c in seg_counts)}")

    if args.noise_levels is not None and n_levels != args.noise_levels:
        print(f"\nError: expected {args.noise_levels} noise levels but found "
              f"{n_levels}.", file=sys.stderr)
        sys.exit(1)

    # --- Step 2: organize ---
    print(f"\nOrganizing {total_files} files into {n_levels} subfolders...")
    sorted_levels = organize_into_subfolders(input_dir, groups)
    for _, nl_id in sorted_levels:
        print(f"  {nl_id}/  — {len(groups[nl_id])} files")

    # --- Step 3: concatenate ---
    concatenate_all(input_dir, sorted_levels)


if __name__ == "__main__":
    main()
