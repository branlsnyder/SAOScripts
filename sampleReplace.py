import os
import json
import argparse

import torch
import soundfile as sf
from einops import rearrange
from stable_audio_tools import get_pretrained_model
from stable_audio_tools.inference.generation import generate_diffusion_cond
from output_naming import build_output_path

AUDIO_EXTENSIONS = {".wav", ".flac", ".mp3", ".ogg", ".aiff", ".aif"}

MODEL_REPO_MAP = {
    "stable-audio-open-small": "stabilityai/stable-audio-open-small",
    "stable-audio-open": "stabilityai/stable-audio-open-1.0",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Audio generation: audio-to-audio (with --indir) or "
                    "text-to-audio (without --indir)."
    )
    parser.add_argument("--model", type=str, default="stable-audio-open-small",
                        choices=list(MODEL_REPO_MAP.keys()),
                        help="Which model to use (default: stable-audio-open-small)")
    parser.add_argument("--indir", type=str, default=None,
                        help="Input directory containing audio files. "
                             "If omitted, runs in text-to-audio mode.")
    parser.add_argument("--outdir", type=str, default=None,
                        help="Output directory (default: Audio/output/)")
    parser.add_argument("--prompt", type=str, default=None,
                        help="Text prompt (required for text-to-audio; applied to every file in audio-to-audio). "
                             "Omit in audio-to-audio to use per-file prompts from --prompt-file.")
    parser.add_argument("--prompt-file", type=str, default=None,
                        help="JSON file mapping filenames to prompts, e.g. "
                             '{\"kick.wav\": \"punchy kick drum\"}. '
                             "Files without an entry fall back to --prompt. "
                             "(audio-to-audio mode only)")
    parser.add_argument("--noise-level", type=float, default=0.3,
                        help="init_noise_level (0-1). Lower keeps more of the "
                             "original structure; higher departs more. (default: 0.3, "
                             "audio-to-audio mode only)")
    parser.add_argument("--steps", type=int, default=8,
                        help="Diffusion steps (default: 8)")
    parser.add_argument("--cfg-scale", type=float, default=1.0,
                        help="Classifier-free guidance scale (default: 1.0)")
    parser.add_argument("--sampler-type", type=str, default="pingpong",
                        help="Sampler type (default: pingpong)")
    parser.add_argument("--seed", type=int, default=-1,
                        help="Random seed (-1 for random per file)")
    parser.add_argument("--duration", type=float, default=None,
                        help="Output duration in seconds. "
                             "Default: match input duration in audio-to-audio, "
                             "or model max in text-to-audio.")
    parser.add_argument("-n", type=int, default=1,
                        help="Number of files to generate (text-to-audio mode only, default: 1)")
    args = parser.parse_args()
    if args.indir is None and args.prompt is None:
        parser.error("--prompt is required when running in text-to-audio mode (no --indir)")
    return args


def discover_audio_files(directory):
    """Return sorted list of audio file paths in directory."""
    files = []
    for name in sorted(os.listdir(directory)):
        if os.path.splitext(name)[1].lower() in AUDIO_EXTENSIONS:
            files.append(os.path.join(directory, name))
    return files


def load_prompt_map(path):
    """Load a JSON file mapping filenames -> prompts."""
    with open(path, "r") as f:
        return json.load(f)


def get_prompt_for_file(filename, prompt_map, default_prompt):
    """Resolve the text prompt for a given file."""
    if prompt_map and filename in prompt_map:
        return prompt_map[filename]
    if default_prompt:
        return default_prompt
    return filename_to_prompt(filename)


def filename_to_prompt(filename):
    """Derive a rough prompt from the filename when no prompt is given."""
    stem = os.path.splitext(filename)[0]
    prompt = stem.replace("_", " ").replace("-", " ")
    return prompt


def main():
    args = parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"

    model_repo = MODEL_REPO_MAP[args.model]
    print(f"Loading model {model_repo}…")
    model, model_config = get_pretrained_model(model_repo)
    model_sr = model_config["sample_rate"]
    sample_size = model_config["sample_size"]
    max_duration = sample_size / model_sr
    model = model.to(device)

    if model.pretransform is not None:
        model.pretransform.model_half = False
        model.pretransform.model.to(torch.float32)

    print(f"Model loaded — sample rate: {model_sr}, max duration: {max_duration:.2f}s")

    if args.indir is not None:
        _run_audio_to_audio(args, model, model_sr, sample_size, max_duration, device)
    else:
        _run_text_to_audio(args, model, model_sr, sample_size, max_duration, device)


def _run_text_to_audio(args, model, model_sr, sample_size, max_duration, device):
    """Generate audio from text prompt only (no input audio)."""
    target_duration = min(args.duration, max_duration) if args.duration else max_duration

    print(f"Mode: text-to-audio")
    print(f"Prompt: \"{args.prompt}\"")
    print(f"Duration: {target_duration:.2f}s  |  Generating {args.n} file(s)")
    print("-" * 60)

    conditioning = [{
        "prompt": args.prompt,
        "seconds_total": target_duration,
    }]

    for i in range(args.n):
        print(f"[{i + 1}/{args.n}] prompt=\"{args.prompt}\"")

        output = generate_diffusion_cond(
            model,
            steps=args.steps,
            cfg_scale=args.cfg_scale,
            conditioning=conditioning,
            sample_size=sample_size,
            sampler_type=args.sampler_type,
            seed=args.seed,
            device=device,
        )

        output = rearrange(output, "b d n -> d (b n)")
        output = (output.to(torch.float32)
                  .div(torch.max(torch.abs(output)))
                  .clamp(-1, 1)
                  .mul(32767)
                  .to(torch.int16)
                  .cpu())

        target_out_samples = int(target_duration * model_sr)
        if output.shape[-1] > target_out_samples:
            output = output[..., :target_out_samples]

        out_path = build_output_path(
            prompt=args.prompt,
            steps=args.steps,
            cfg_scale=args.cfg_scale,
            seed=args.seed,
            sampler_type=args.sampler_type,
            duration=target_duration,
            model=args.model,
            index=i,
        )
        sf.write(out_path, output.numpy().T, model_sr)
        print(f"  → saved {out_path}")

    print("-" * 60)
    print("Done. {} file(s) written to Audio/output/".format(args.n))


def _run_audio_to_audio(args, model, model_sr, sample_size, max_duration, device):
    """Regenerate audio from input files guided by text prompts."""
    if not os.path.isdir(args.indir):
        raise SystemExit(f"Input directory not found: {args.indir}")

    audio_files = discover_audio_files(args.indir)
    if not audio_files:
        raise SystemExit(f"No audio files found in {args.indir}")

    prompt_map = load_prompt_map(args.prompt_file) if args.prompt_file else None

    print(f"Mode: audio-to-audio")
    print(f"Input:  {args.indir}  ({len(audio_files)} files)")
    print(f"Noise level: {args.noise_level}")
    if args.prompt:
        print(f"Global prompt: \"{args.prompt}\"")
    elif args.prompt_file:
        print(f"Per-file prompts from: {args.prompt_file}")
    else:
        print("No prompt supplied — deriving prompts from filenames")
    print("-" * 60)

    for i, filepath in enumerate(audio_files):
        filename = os.path.basename(filepath)
        prompt = get_prompt_for_file(filename, prompt_map, args.prompt)

        audio_data, in_sr = sf.read(filepath, dtype="float32")
        audio_tensor = torch.from_numpy(audio_data)
        if audio_tensor.dim() == 1:
            audio_tensor = audio_tensor.unsqueeze(0)
        else:
            audio_tensor = audio_tensor.T

        input_duration = audio_tensor.shape[-1] / in_sr
        if args.duration is not None:
            target_duration = min(args.duration, max_duration)
        else:
            target_duration = min(input_duration, max_duration)

        target_samples = int(target_duration * model_sr)
        target_samples = min(target_samples, sample_size)

        init_audio = (in_sr, audio_tensor)

        conditioning = [{
            "prompt": prompt,
            "seconds_total": target_duration,
        }]

        print(f"[{i + 1}/{len(audio_files)}] {filename}  "
              f"({input_duration:.1f}s @ {in_sr}Hz)  →  "
              f"noise={args.noise_level}  prompt=\"{prompt}\"")

        output = generate_diffusion_cond(
            model,
            steps=args.steps,
            cfg_scale=args.cfg_scale,
            conditioning=conditioning,
            sample_size=sample_size,
            sampler_type=args.sampler_type,
            seed=args.seed,
            device=device,
            init_audio=init_audio,
            init_noise_level=args.noise_level,
        )

        output = rearrange(output, "b d n -> d (b n)")
        output = (output.to(torch.float32)
                  .div(torch.max(torch.abs(output)))
                  .clamp(-1, 1)
                  .mul(32767)
                  .to(torch.int16)
                  .cpu())

        target_out_samples = int(target_duration * model_sr)
        if output.shape[-1] > target_out_samples:
            output = output[..., :target_out_samples]

        out_path = build_output_path(
            input_filename=filename,
            noise_level=args.noise_level,
            steps=args.steps,
            cfg_scale=args.cfg_scale,
            seed=args.seed,
            sampler_type=args.sampler_type,
            duration=target_duration,
            model=args.model,
        )
        sf.write(out_path, output.numpy().T, model_sr)
        print(f"  → saved {out_path}")

    print("-" * 60)
    print(f"Done. {len(audio_files)} files written to Audio/output/")


if __name__ == "__main__":
    main()
