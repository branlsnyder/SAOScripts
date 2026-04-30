#!/usr/bin/env python3
"""
Pad silence onto the end of one or more audio files so each matches the duration
(in seconds) of a reference audio file.

Usage:
    python pad_to_reference_duration.py <reference_audio> <target_audio> [output_audio]
    python pad_to_reference_duration.py <reference_audio> <targets_folder> --outdir <dir>

Arguments:
    reference_audio   WAV/other format readable by soundfile; defines target duration
    target_audio      Single file to pad
    targets_folder    Directory of audio files (see --glob)
    output_audio      Output path for single-file mode (default: <name>_padded.wav)

Options:
    --outdir          Required when target is a folder; padded files written here
    --glob            Glob pattern relative to folder (default: *.wav)
    --truncate        If a target is longer than the reference, trim the end instead of error

Examples:
    python pad_to_reference_duration.py ref.wav shorter.wav padded.wav
    python pad_to_reference_duration.py ref.wav segments/ --outdir segments_padded/
"""

from __future__ import annotations

import argparse
import glob
import os
import sys

import numpy as np
import soundfile as sf


AUDIO_EXTENSIONS = (".wav", ".flac", ".ogg", ".aiff", ".aif")


def _reference_duration_seconds(path: str) -> float:
    info = sf.info(path)
    return info.frames / float(info.samplerate)


def _list_targets(folder: str, pattern: str) -> list[str]:
    search = os.path.join(folder, pattern)
    files = sorted(glob.glob(search))
    if not files:
        print(f"Error: no files matched {search}", file=sys.stderr)
        sys.exit(1)
    return files


def _pad_or_trim(
    data: np.ndarray,
    sr: int,
    ref_duration: float,
    truncate: bool,
    path_label: str,
) -> np.ndarray:
    cur_frames = data.shape[0]
    cur_duration = cur_frames / float(sr)
    target_frames = int(round(ref_duration * sr))

    if cur_frames > target_frames:
        if not truncate:
            print(
                f"Error: {path_label} is longer than reference "
                f"({cur_duration:.6f}s > {ref_duration:.6f}s). "
                f"Use --truncate to shorten it.",
                file=sys.stderr,
            )
            sys.exit(1)
        return data[:target_frames]

    pad_frames = target_frames - cur_frames
    if pad_frames <= 0:
        return data

    if data.ndim == 1:
        return np.pad(data, (0, pad_frames), mode="constant", constant_values=0)
    return np.pad(data, ((0, pad_frames), (0, 0)), mode="constant", constant_values=0)


def _process_one(
    ref_duration: float,
    input_path: str,
    output_path: str,
    truncate: bool,
) -> None:
    data, sr = sf.read(input_path, always_2d=False)
    if data.ndim > 2:
        print(f"Error: unsupported shape {data.shape} in {input_path}", file=sys.stderr)
        sys.exit(1)

    out = _pad_or_trim(data, sr, ref_duration, truncate, input_path)

    subtype = sf.info(input_path).subtype
    out_dir = os.path.dirname(os.path.abspath(output_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    sf.write(output_path, out, sr, subtype=subtype)

    final_dur = out.shape[0] / float(sr)
    print(f"{input_path} -> {output_path}  ({final_dur:.6f}s)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pad trailing silence so audio matches reference duration."
    )
    parser.add_argument("reference", help="Reference audio file (defines duration)")
    parser.add_argument("target", help="Audio file or folder of audio files to pad")
    parser.add_argument(
        "output",
        nargs="?",
        default=None,
        help="Output file (single-file mode only; default <stem>_padded.wav)",
    )
    parser.add_argument(
        "--outdir",
        default=None,
        help="Output directory when target is a folder",
    )
    parser.add_argument(
        "--glob",
        default="*.wav",
        help='Glob pattern inside folder (default: "*.wav")',
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Trim targets longer than the reference instead of failing",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.reference):
        print(f"Error: reference not found: {args.reference}", file=sys.stderr)
        sys.exit(1)

    ref_duration = _reference_duration_seconds(args.reference)

    if os.path.isdir(args.target):
        if not args.outdir:
            print("Error: --outdir is required when target is a folder", file=sys.stderr)
            sys.exit(1)
        targets = _list_targets(args.target, args.glob)
        os.makedirs(args.outdir, exist_ok=True)
        for src in targets:
            base = os.path.basename(src)
            dst = os.path.join(args.outdir, base)
            _process_one(ref_duration, src, dst, args.truncate)
        print(f"Reference duration: {ref_duration:.6f}s ({args.reference})")
        return

    if not os.path.isfile(args.target):
        print(f"Error: target not found: {args.target}", file=sys.stderr)
        sys.exit(1)

    if args.outdir:
        print("Error: --outdir applies only when target is a folder", file=sys.stderr)
        sys.exit(1)

    if args.output:
        out_path = args.output
    else:
        stem, ext = os.path.splitext(args.target)
        ext = ext if ext.lower() in AUDIO_EXTENSIONS else ".wav"
        out_path = f"{stem}_padded{ext}"

    _process_one(ref_duration, args.target, out_path, args.truncate)
    print(f"Reference duration: {ref_duration:.6f}s ({args.reference})")


if __name__ == "__main__":
    main()
