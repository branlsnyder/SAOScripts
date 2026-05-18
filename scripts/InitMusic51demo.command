#!/bin/bash
# Double-click in Finder: opens Terminal in StableAudioWorkspace with venv active.

set -euo pipefail

PROJ_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJ_ROOT"

VENV_ACTIVATE="$PROJ_ROOT/venv/bin/activate"
if [[ ! -f "$VENV_ACTIVATE" ]]; then
  echo "error: venv not found at $VENV_ACTIVATE" >&2
  echo "Create it from this folder, then try again." >&2
  read -r -p "Press Enter to close…"
  exit 1
fi

# shellcheck source=/dev/null
source "$VENV_ACTIVATE"

echo "StableAudioWorkspace: $PROJ_ROOT"
echo "Python: $(command -v python) ($(python --version 2>&1))"
echo "venv active — run scripts from here (e.g. bash scripts/music51_01.sh)"
echo

exec bash -l
