#!/usr/bin/env python3
"""
Remove stretches of digital silence from a WAV file.

Usage:
    python remove_silence.py <input_file> [output_file] [options]

Arguments:
    input_file      Path to the source WAV file (or directory of WAV files)
    output_file     (Optional) Output WAV path. Defaults to <name>_no_silence.wav
                    When input is a directory, this is ignored; cleaned files are
                    written in-place or to a parallel output directory with --outdir.

Options:
    --min-silence   Minimum silence duration in seconds to remove (default: 1.0)
    --threshold     Amplitude threshold as a fraction of max value (0.0–1.0)
                    below which a sample is considered silent (default: 0.001)
    --in-place      Overwrite the original file(s)
    --outdir        When processing a directory, write cleaned files here

Examples:
    # Single file — writes alto_recorder_UNT_no_silence.wav
    python remove_silence.py audio.wav

    # Single file — custom output and 0.5s threshold
    python remove_silence.py audio.wav cleaned.wav --min-silence 0.5

    # Overwrite original
    python remove_silence.py audio.wav --in-place

    # Process every WAV in a directory
    python remove_silence.py segments/ --outdir segments_clean/

In a shell pipeline (before corpus segmentation):
    python3 SomaxCorpusWork/pythonScripts/remove_silence.py \\
        "$AUDIO_FILE" "${AUDIO_FILE%.wav}_no_silence.wav" \\
        --min-silence 1.0
"""

import argparse
import array
import glob
import os
import sys
import wave


def _read_wav(path: str) -> tuple[bytes, int, int, int, int]:
    """Read a WAV file, returning (raw_bytes, sr, n_channels, sampwidth, n_frames)."""
    with wave.open(path, "rb") as w:
        sr = w.getframerate()
        n_channels = w.getnchannels()
        sampwidth = w.getsampwidth()
        n_frames = w.getnframes()
        raw = w.readframes(n_frames)
    return raw, sr, n_channels, sampwidth, n_frames


def _write_wav(path: str, raw: bytes, sr: int, n_channels: int, sampwidth: int) -> None:
    """Write raw PCM bytes to a WAV file."""
    with wave.open(path, "wb") as w:
        w.setnchannels(n_channels)
        w.setsampwidth(sampwidth)
        w.setframerate(sr)
        w.writeframes(raw)


def _samples_from_bytes(raw: bytes, sampwidth: int) -> array.array:
    """Convert raw PCM bytes to an array of signed integer samples."""
    if sampwidth == 2:
        return array.array("h", raw)
    if sampwidth == 4:
        return array.array("i", raw)
    if sampwidth == 1:
        unsigned = array.array("B", raw)
        return array.array("h", [s - 128 for s in unsigned])
    if sampwidth == 3:
        samples = array.array("i")
        for i in range(0, len(raw), 3):
            val = int.from_bytes(raw[i : i + 3], byteorder="little", signed=True)
            samples.append(val)
        return samples
    raise ValueError(f"Unsupported sample width: {sampwidth} bytes")


def _max_sample_value(sampwidth: int) -> int:
    """Peak absolute value for a given sample width."""
    if sampwidth == 1:
        return 127
    return (1 << (sampwidth * 8 - 1)) - 1


def find_silent_regions(
    samples: array.array,
    sr: int,
    n_channels: int,
    min_silence_sec: float,
    threshold_frac: float,
    sampwidth: int,
) -> list[tuple[int, int]]:
    """Return a list of (start_frame, end_frame) for silent stretches >= min_silence_sec."""
    abs_thresh = threshold_frac * _max_sample_value(sampwidth)
    n_frames = len(samples) // n_channels
    min_silence_frames = int(min_silence_sec * sr)

    regions: list[tuple[int, int]] = []
    run_start: int | None = None

    for f in range(n_frames):
        base = f * n_channels
        loud = False
        for ch in range(n_channels):
            if abs(samples[base + ch]) > abs_thresh:
                loud = True
                break

        if not loud:
            if run_start is None:
                run_start = f
        else:
            if run_start is not None:
                if f - run_start >= min_silence_frames:
                    regions.append((run_start, f))
                run_start = None

    if run_start is not None and n_frames - run_start >= min_silence_frames:
        regions.append((run_start, n_frames))

    return regions


def remove_silence(
    input_path: str,
    output_path: str,
    min_silence: float = 1.0,
    threshold: float = 0.001,
) -> None:
    """Remove long silent stretches from a WAV file and write the result."""
    raw, sr, n_channels, sampwidth, n_frames = _read_wav(input_path)
    bytes_per_frame = n_channels * sampwidth
    duration = n_frames / sr

    print(f"  Input:    {input_path}")
    print(f"  SR: {sr}  Channels: {n_channels}  Bit depth: {sampwidth * 8}")
    print(f"  Duration: {duration:.3f}s  ({n_frames} frames)")

    samples = _samples_from_bytes(raw, sampwidth)
    regions = find_silent_regions(samples, sr, n_channels, min_silence, threshold, sampwidth)

    if not regions:
        print(f"  No silent regions >= {min_silence:.3f}s found — copying unchanged.")
        if os.path.abspath(input_path) != os.path.abspath(output_path):
            _write_wav(output_path, raw, sr, n_channels, sampwidth)
        print()
        return

    total_silent_frames = sum(end - start for start, end in regions)
    total_silent_sec = total_silent_frames / sr
    print(f"  Found {len(regions)} silent region(s) totalling {total_silent_sec:.3f}s:")
    for i, (start, end) in enumerate(regions):
        s_sec = start / sr
        e_sec = end / sr
        print(f"    [{i}] {s_sec:.3f}s – {e_sec:.3f}s  ({e_sec - s_sec:.3f}s)")

    kept_chunks: list[bytes] = []
    prev_end = 0
    for start, end in regions:
        if prev_end < start:
            kept_chunks.append(raw[prev_end * bytes_per_frame : start * bytes_per_frame])
        prev_end = end
    if prev_end < n_frames:
        kept_chunks.append(raw[prev_end * bytes_per_frame : n_frames * bytes_per_frame])

    out_raw = b"".join(kept_chunks)
    out_frames = len(out_raw) // bytes_per_frame
    out_dur = out_frames / sr

    _write_wav(output_path, out_raw, sr, n_channels, sampwidth)

    removed_sec = duration - out_dur
    print(f"  Output:   {output_path}")
    print(f"  Duration: {out_dur:.3f}s  (removed {removed_sec:.3f}s)")
    print()


def process_directory(
    input_dir: str,
    output_dir: str | None,
    in_place: bool,
    min_silence: float,
    threshold: float,
) -> None:
    """Process all WAV files in a directory."""
    wav_files = sorted(glob.glob(os.path.join(input_dir, "*.wav")))
    if not wav_files:
        print(f"Error: no .wav files found in {input_dir}", file=sys.stderr)
        sys.exit(1)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    print(f"Processing {len(wav_files)} WAV file(s) in {input_dir}/")
    print()

    for path in wav_files:
        basename = os.path.basename(path)
        if in_place:
            out = path
        elif output_dir:
            out = os.path.join(output_dir, basename)
        else:
            name, ext = os.path.splitext(basename)
            out = os.path.join(input_dir, f"{name}_no_silence{ext}")

        remove_silence(path, out, min_silence, threshold)


def main():
    parser = argparse.ArgumentParser(
        description="Remove stretches of digital silence from WAV file(s)."
    )
    parser.add_argument(
        "input",
        help="Path to a WAV file or a directory of WAV files",
    )
    parser.add_argument(
        "output",
        nargs="?",
        default=None,
        help="Output WAV path (ignored when input is a directory; use --outdir instead)",
    )
    parser.add_argument(
        "--min-silence",
        type=float,
        default=1.0,
        help="Minimum silence duration in seconds to remove (default: 1.0)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.001,
        help="Amplitude threshold as a fraction of max (default: 0.001)",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Overwrite the original file(s)",
    )
    parser.add_argument(
        "--outdir",
        default=None,
        help="Output directory when processing a directory of WAV files",
    )
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: input not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    if not 0.0 <= args.threshold <= 1.0:
        print("Error: --threshold must be between 0.0 and 1.0", file=sys.stderr)
        sys.exit(1)

    if args.min_silence <= 0:
        print("Error: --min-silence must be positive", file=sys.stderr)
        sys.exit(1)

    print(f"Settings: min_silence={args.min_silence}s  threshold={args.threshold}")
    print()

    if os.path.isdir(args.input):
        process_directory(args.input, args.outdir, args.in_place, args.min_silence, args.threshold)
    else:
        if args.in_place:
            out = args.input
        elif args.output:
            out = args.output
        else:
            name, ext = os.path.splitext(args.input)
            out = f"{name}_no_silence{ext}"

        remove_silence(args.input, out, args.min_silence, args.threshold)

    print("Done.")


if __name__ == "__main__":
    main()
