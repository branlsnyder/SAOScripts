
#!/usr/bin/env bash
#
# sampleReplace_darkAmbient.sh
#
# Quick script to generate 3 samples (10s each) with the prompt
# "dark ambient texture" using sampleReplace.py.
#
# Usage:
#   bash scripts/sampleReplace_darkAmbient.sh

set -euo pipefail

PROJ_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJ_ROOT"


# python python/sampleReplace.py --prompt "Alvin Lucier I'm Sitting in a Room" -n 3 --duration 10
python python/sampleReplace.py --prompt "calm soft spoken male radio voice speaking in english in an even emotionless matter of fact manner" -n 3 --duration 10

echo ""
echo "==== Done ===="
