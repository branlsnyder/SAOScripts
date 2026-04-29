#!/usr/bin/env python3
"""
Organize WAV files from multiCorpus1_joelle2digital into subfolders
grouped by noise_level ID.

Each file like:
  segment-016_sm_swinit_noise_level-0.7154_nl0.7154_s8_cfg1_pp_d11_030_20260423_102110.wav
gets moved into a subfolder named:
  noise_level-0.7154/
"""

import os
import re
import shutil
import sys

SOURCE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "multiCorpus1_joelle2digital",
)

NOISE_LEVEL_RE = re.compile(r"(noise_level-[\d.]+)_")


def main():
    if not os.path.isdir(SOURCE_DIR):
        print(f"Error: source directory not found: {SOURCE_DIR}", file=sys.stderr)
        sys.exit(1)

    wav_files = [f for f in os.listdir(SOURCE_DIR) if f.endswith(".wav")]
    wav_files.sort()

    if not wav_files:
        print("No .wav files found.", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(wav_files)} WAV files in {SOURCE_DIR}")

    groups: dict[str, list[str]] = {}
    unmatched = []

    for fname in wav_files:
        m = NOISE_LEVEL_RE.search(fname)
        if m:
            nl_id = m.group(1)
            groups.setdefault(nl_id, []).append(fname)
        else:
            unmatched.append(fname)

    if unmatched:
        print(f"Warning: {len(unmatched)} files did not match noise_level pattern:")
        for f in unmatched:
            print(f"  {f}")

    print(f"Found {len(groups)} unique noise levels\n")

    for nl_id in sorted(groups, key=lambda x: float(x.split("-")[1])):
        files = groups[nl_id]
        subfolder = os.path.join(SOURCE_DIR, nl_id)
        os.makedirs(subfolder, exist_ok=True)

        for fname in sorted(files):
            src = os.path.join(SOURCE_DIR, fname)
            dst = os.path.join(subfolder, fname)
            shutil.move(src, dst)

        print(f"  {nl_id}/  — {len(files)} files")

    print(f"\nDone. Organized {len(wav_files)} files into {len(groups)} subfolders.")


if __name__ == "__main__":
    main()
