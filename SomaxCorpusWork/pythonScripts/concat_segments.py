#!/usr/bin/env python3
"""
Concatenate a folder of segment WAV files into a single audio file.

Usage:
    python concat_segments.py <segments_folder> [output_file]

Arguments:
    segments_folder   Path to the folder containing segment_NNN.wav files
    output_file       (Optional) Output WAV path. Defaults to <folder_name>.wav

Segments are sorted by their numeric index (segment_000, segment_001, …).
All segments must share the same sample rate, channel count, and bit depth.
"""

import argparse
import glob
import os
import re
import sys
import wave


def find_segments(folder: str) -> list[str]:
    """Find and sort segment WAV files by their numeric index."""
    pattern = os.path.join(folder, "segment_*.wav")
    files = glob.glob(pattern)
    if not files:
        pattern = os.path.join(folder, "segment-*.wav")
        files = glob.glob(pattern)
    if not files:
        print(f"Error: no segment*.wav files found in {folder}", file=sys.stderr)
        sys.exit(1)

    def sort_key(path: str) -> int:
        match = re.search(r"segment[-_](\d+)", os.path.basename(path))
        return int(match.group(1)) if match else 0

    files.sort(key=sort_key)
    return files


def concat_segments(segments_folder: str, output_file: str) -> None:
    segments = find_segments(segments_folder)
    print(f"Found {len(segments)} segments in {segments_folder}/")

    with wave.open(segments[0], "rb") as first:
        sr = first.getframerate()
        n_channels = first.getnchannels()
        sampwidth = first.getsampwidth()

    print(f"Format: SR={sr}  Channels={n_channels}  Bit depth={sampwidth * 8}")
    print(f"Output: {output_file}")
    print()

    total_frames = 0
    with wave.open(output_file, "wb") as wav_out:
        wav_out.setnchannels(n_channels)
        wav_out.setsampwidth(sampwidth)
        wav_out.setframerate(sr)

        for path in segments:
            with wave.open(path, "rb") as seg:
                if seg.getframerate() != sr or seg.getnchannels() != n_channels or seg.getsampwidth() != sampwidth:
                    print(
                        f"Error: {os.path.basename(path)} has mismatched format "
                        f"(SR={seg.getframerate()}, Ch={seg.getnchannels()}, "
                        f"Bits={seg.getsampwidth() * 8})",
                        file=sys.stderr,
                    )
                    sys.exit(1)

                frames = seg.getnframes()
                wav_out.writeframes(seg.readframes(frames))
                total_frames += frames

            dur = frames / sr
            print(f"  {os.path.basename(path):>20s}  {frames:>8d} frames  ({dur:.6f}s)")

    total_duration = total_frames / sr
    print()
    print(f"Total: {total_frames} frames  ({total_duration:.6f}s)")
    print(f"Written to {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Concatenate segment WAV files into a single audio file."
    )
    parser.add_argument("segments_folder", help="Folder containing segment_NNN.wav files")
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
