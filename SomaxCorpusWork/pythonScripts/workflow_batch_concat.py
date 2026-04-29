#!/usr/bin/env python3
"""
Batch-concatenate all noise-level subfolders inside multiCorpus1_joelle2digital/.

For each noise_level-X.XXXX/ subfolder, concatenates the 16 segments into a
single WAV file.  Output files are placed in a dedicated subfolder and prefixed
with a zero-padded index (01–40) so they sort by ascending noise level in any
file browser.
"""

import os
import re
import sys

from concat_segments import concat_segments

SOURCE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "multiCorpus1_joelle2digital",
)
OUTPUT_DIR = os.path.join(SOURCE_DIR, "concatenated")

NOISE_LEVEL_RE = re.compile(r"^noise_level-([\d.]+)$")


def main():
    if not os.path.isdir(SOURCE_DIR):
        print(f"Error: source directory not found: {SOURCE_DIR}", file=sys.stderr)
        sys.exit(1)

    subfolders = []
    for name in os.listdir(SOURCE_DIR):
        m = NOISE_LEVEL_RE.match(name)
        if m and os.path.isdir(os.path.join(SOURCE_DIR, name)):
            subfolders.append((float(m.group(1)), name))

    subfolders.sort(key=lambda x: x[0])

    if not subfolders:
        print("No noise_level-* subfolders found.", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(subfolders)} noise-level subfolders")
    print(f"Output directory: {OUTPUT_DIR}\n")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for idx, (nl_val, folder_name) in enumerate(subfolders, start=1):
        folder_path = os.path.join(SOURCE_DIR, folder_name)
        out_name = f"{idx:02d}_{folder_name}.wav"
        out_path = os.path.join(OUTPUT_DIR, out_name)

        print(f"{'=' * 60}")
        print(f"[{idx:02d}/40]  {folder_name}  ->  {out_name}")
        print(f"{'=' * 60}")
        concat_segments(folder_path, out_path)
        print()

    print(f"Done. {len(subfolders)} concatenated files written to:\n  {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
