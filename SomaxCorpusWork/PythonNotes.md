# Python Notes

# Segmenting Audio file from .pickle

## Default output folder (uses corpus name + "Segments")

python segment_corpus.py Fabbrizio2c.wav Fabbrizio2c.pickle

## Custom output folder

python segment_corpus.py Joelle.wav Joelle.pickle MyCustomFolder

## Help

python segment_corpus.py --help

# interpolate joelle to digital noise

python interpolateGen.py --init-audio "/Users/brandonwoosnyder/Dropbox/docs-d/00_UCI_2025-2026/Music 237 Somax/Current Project/JoelleSegments" --prompt "growling dubstep bass" --param init_noise_level --start 0.60 --end 0.9 -n 40 --match-source-audio

# interpolate joelle to reverb and resonance
