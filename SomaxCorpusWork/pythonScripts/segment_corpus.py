#!/usr/bin/env python3
"""
Split a Somax2 audio corpus into individual segment WAV files.

Usage:
    python segment_corpus.py <audio_file> <pickle_file> [output_folder]

Arguments:
    audio_file      Path to the source WAV file
    pickle_file     Path to the Somax2 .pickle corpus file
    output_folder   (Optional) Output folder name. Defaults to <corpus_name>Segments

The .pickle file is a gzip-compressed pickle produced by Somax2's corpus builder.
Each event/segment has an onset time and duration in seconds. This script extracts
each segment as its own WAV file, extending the first and last segments so that the
full original audio duration is covered exactly.
"""

import argparse
import gzip
import os
import pickle
import sys
import wave


# ---------------------------------------------------------------------------
# Generic unpickler – loads Somax2 pickles without requiring Somax2 installed
# ---------------------------------------------------------------------------

_class_cache: dict[tuple[str, str], type] = {}


def _make_generic_class(module: str, name: str) -> type:
    key = (module, name)
    if key in _class_cache:
        return _class_cache[key]

    class GenericObj:
        _somax_module = module
        _somax_name = name

        def __init__(self, *args, **kwargs):
            self._init_args = args
            self._init_kwargs = kwargs

        def __setstate__(self, state):
            if isinstance(state, dict):
                self.__dict__.update(state)

    GenericObj.__name__ = name
    GenericObj.__qualname__ = name
    _class_cache[key] = GenericObj
    return GenericObj


class SomaxUnpickler(pickle.Unpickler):
    """Unpickler that stubs out Somax2 classes with generic attribute bags."""

    def find_class(self, module: str, name: str):
        try:
            return super().find_class(module, name)
        except (ModuleNotFoundError, AttributeError):
            return _make_generic_class(module, name)


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def load_corpus(pickle_path: str):
    """Load a gzip-compressed Somax2 AudioCorpus pickle."""
    with gzip.open(pickle_path, "rb") as f:
        return SomaxUnpickler(f).load()


def segment_audio(audio_path: str, pickle_path: str, output_folder: str) -> None:
    corpus = load_corpus(pickle_path)
    events = corpus.events
    num_events = len(events)

    if num_events == 0:
        print("Error: corpus contains no events.", file=sys.stderr)
        sys.exit(1)

    print(f"Corpus:     {corpus.name}")
    print(f"Events:     {num_events}")
    print(f"Corpus SR:  {corpus.sr}")

    with wave.open(audio_path, "rb") as wav_in:
        sr = wav_in.getframerate()
        n_channels = wav_in.getnchannels()
        sampwidth = wav_in.getsampwidth()
        total_frames = wav_in.getnframes()
        all_frames = wav_in.readframes(total_frames)

    wav_duration = total_frames / sr
    bytes_per_frame = n_channels * sampwidth

    print(f"Audio file: {audio_path}")
    print(f"  SR: {sr}  Channels: {n_channels}  Duration: {wav_duration:.6f}s")
    print(f"Output:     {output_folder}/")
    print()

    os.makedirs(output_folder, exist_ok=True)

    for i, event in enumerate(events):
        onset = event._absolute_onset
        duration = event._absolute_duration

        # First segment starts at 0; last segment extends to true file end
        start_frame = 0 if i == 0 else int(round(onset * sr))
        if i == num_events - 1:
            end_frame = total_frames
        else:
            end_frame = int(round((onset + duration) * sr))

        start_frame = max(0, min(start_frame, total_frames))
        end_frame = max(start_frame, min(end_frame, total_frames))

        segment_data = all_frames[start_frame * bytes_per_frame : end_frame * bytes_per_frame]

        out_path = os.path.join(output_folder, f"segment_{i:03d}.wav")
        with wave.open(out_path, "wb") as wav_out:
            wav_out.setnchannels(n_channels)
            wav_out.setsampwidth(sampwidth)
            wav_out.setframerate(sr)
            wav_out.writeframes(segment_data)

        seg_dur = (end_frame - start_frame) / sr
        print(f"  [{i:3d}] {out_path}  onset={onset:.6f}s  dur={seg_dur:.6f}s")

    # Verify
    total_output_frames = 0
    for i in range(num_events):
        with wave.open(os.path.join(output_folder, f"segment_{i:03d}.wav"), "rb") as w:
            total_output_frames += w.getnframes()

    print()
    print(f"Original WAV:    {total_frames} frames  ({wav_duration:.6f}s)")
    print(f"Sum of segments: {total_output_frames} frames  ({total_output_frames / sr:.6f}s)")
    if total_output_frames == total_frames:
        print("OK – segment durations match original exactly.")
    else:
        diff = abs(total_output_frames - total_frames)
        print(f"WARNING – mismatch of {diff} frames ({diff / sr:.6f}s).")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Split a Somax2 audio corpus into individual segment WAV files."
    )
    parser.add_argument("audio_file", help="Path to the source WAV file")
    parser.add_argument("pickle_file", help="Path to the Somax2 .pickle corpus file")
    parser.add_argument(
        "output_folder",
        nargs="?",
        default=None,
        help="Output folder (default: <corpus_name>Segments)",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.audio_file):
        print(f"Error: audio file not found: {args.audio_file}", file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(args.pickle_file):
        print(f"Error: pickle file not found: {args.pickle_file}", file=sys.stderr)
        sys.exit(1)

    if args.output_folder is None:
        corpus = load_corpus(args.pickle_file)
        args.output_folder = f"{corpus.name}Segments"

    segment_audio(args.audio_file, args.pickle_file, args.output_folder)


if __name__ == "__main__":
    main()
