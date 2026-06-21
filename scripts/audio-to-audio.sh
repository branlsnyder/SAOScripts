
#!/usr/bin/env bash
#


set -euo pipefail

PROJ_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJ_ROOT"



# python python/interpolateGen.py --init-audio "Audio/voice-sample.wav" --prompt "" --param init_noise_level --start 0.1 --end 0.9 -n 10
# python python/interpolateGen.py --init-audio "Audio/voice-sample.wav" --prompt "growling dubstep bass vocal fry" --param init_noise_level --start 0.1 --end 0.9 -n 15
python python/interpolateGen.py --init-audio "Audio/voice-sample.wav" --prompt "solo string bass" --param init_noise_level --start 0.1 --end 0.9 -n 15

echo ""
echo "==== Done ===="
