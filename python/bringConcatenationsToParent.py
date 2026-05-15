#!/usr/bin/env python3
"""
Move every audio file from nested `concatenated/` folders up to a destination root.

`workflow_noise_level_concat.py` writes per–noise-level mixes under each run folder
as `<run>/concatenated/*.wav`. By default this script searches under *search_dir*
and moves those files to the top level of the same directory. With ``--dest``,
files are moved to *dest_dir* instead (e.g. search each prompt's ``OUTDIR`` but
flatten into the pipeline ``OUTPUT_DIR``).

If two sources would produce the same basename at the destination, the destination
name is prefixed with the immediate parent folder of `concatenated` (usually the
prompt sweep folder) to avoid overwrites.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

AUDIO_SUFFIXES = frozenset({".wav", ".flac", ".ogg", ".mp3", ".aif", ".aiff"})


def is_audio(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in AUDIO_SUFFIXES


def find_concatenated_dirs(root: Path) -> list[Path]:
    return sorted(
        p
        for p in root.rglob("concatenated")
        if p.is_dir() and p.name == "concatenated" and p.resolve() != root.resolve()
    )


def unique_dest(dest_root: Path, preferred: Path, parent_of_concat: Path) -> Path:
    if not preferred.exists():
        return preferred
    stem = parent_of_concat.name
    candidate = dest_root / f"{stem}__{preferred.name}"
    n = 2
    while candidate.exists():
        candidate = dest_root / f"{stem}__{n}__{preferred.name}"
        n += 1
    return candidate


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Move audio files from concatenated/ subfolders to a directory root."
    )
    parser.add_argument(
        "search_dir",
        type=Path,
        help="Directory tree to search for concatenated/ folders (e.g. one prompt's OUTDIR, or OUTPUT_DIR).",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=None,
        help="Where to move audio files (default: same as search_dir).",
    )
    args = parser.parse_args()
    search_root = args.search_dir.expanduser().resolve()
    if not search_root.is_dir():
        print(f"Error: not a directory: {search_root}", file=sys.stderr)
        sys.exit(1)

    dest_root = (
        args.dest.expanduser().resolve() if args.dest is not None else search_root
    )
    dest_root.mkdir(parents=True, exist_ok=True)

    concat_dirs = find_concatenated_dirs(search_root)
    if not concat_dirs:
        print(f"No 'concatenated' subfolders under {search_root}")
        return

    moved = 0
    for concat_dir in concat_dirs:
        parent = concat_dir.parent
        for path in sorted(concat_dir.iterdir()):
            if not is_audio(path):
                continue
            dest = unique_dest(dest_root, dest_root / path.name, parent)
            shutil.move(str(path), str(dest))
            print(f"  {path}  ->  {dest}")
            moved += 1
        try:
            concat_dir.rmdir()
        except OSError:
            pass

    print(f"\nDone — moved {moved} file(s) to {dest_root}")


if __name__ == "__main__":
    main()
