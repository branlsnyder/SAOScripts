import os
import argparse
import glob
from datetime import datetime
import numpy as np
import torch
import soundfile as sf
from stable_audio_tools.inference.generation import generate_diffusion_cond
from output_naming import build_output_path, OUTPUT_DIR
from audio_utils import MODEL_REPO_MAP, get_device, load_model, postprocess_output

AUDIO_EXTENSIONS = {".wav", ".flac", ".ogg", ".mp3", ".aif", ".aiff"}

INT_PARAMS = {"steps", "seed"}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate multiple audio outputs sweeping a parameter linearly. "
                    "--init-audio accepts a single file or a folder of audio files."
    )
    parser.add_argument("--model", type=str, default="stable-audio-open-small",
                        choices=list(MODEL_REPO_MAP.keys()),
                        help="Which model to use (default: stable-audio-open-small)")
    parser.add_argument("--prompt", type=str, default="dubstep bass growls",
                        help="Text prompt for generation")
    parser.add_argument("--duration", type=float, default=11,
                        help="Total duration in seconds")
    parser.add_argument("--param", type=str, default="cfg_scale",
                        choices=["cfg_scale", "steps", "sigma_min", "sigma_max",
                                 "init_noise_level", "seed"],
                        help="Parameter to sweep")
    parser.add_argument("--start", type=float, default=0,
                        help="Start value for the swept parameter")
    parser.add_argument("--end", type=float, default=15,
                        help="End value for the swept parameter")
    parser.add_argument("-n", type=int, default=5,
                        help="Number of outputs to generate")
    parser.add_argument("--steps", type=int, default=8,
                        help="Diffusion steps (used when not sweeping 'steps')")
    parser.add_argument("--cfg_scale", type=float, default=1,
                        help="CFG scale (used when not sweeping 'cfg_scale')")
    parser.add_argument("--sigma_min", type=float, default=0.3,
                        help="Sigma min (used when not sweeping 'sigma_min')")
    parser.add_argument("--sigma_max", type=float, default=500,
                        help="Sigma max (used when not sweeping 'sigma_max')")
    parser.add_argument("--sampler_type", type=str, default="pingpong")
    parser.add_argument("--init-audio", type=str, default=None,
                        help="Path to an audio file OR a folder of audio files "
                             "for audio-to-audio mode. If omitted, runs text-to-audio.")
    parser.add_argument("--init_noise_level", type=float, default=0.3,
                        help="Init noise level for audio-to-audio (default: 0.3; "
                             "used when not sweeping 'init_noise_level')")
    parser.add_argument("--seed", type=int, default=-1,
                        help="Random seed (-1 for random; used when not sweeping 'seed')")
    parser.add_argument("--match-source-length", action="store_true", default=False,
                        help="Trim each output to the exact duration of its source "
                             "init-audio file. Only applies in audio-to-audio mode.")
    parser.add_argument("--outdir", type=str, default=None,
                        help="Output directory. If omitted, a timestamped subfolder "
                             "is created inside Audio/output/.")
    return parser.parse_args()


def load_init_audio(audio_path):
    """Read an audio file and return ((sample_rate, tensor), duration_seconds)."""
    audio_data, in_sr = sf.read(audio_path, dtype="float32")
    source_duration = len(audio_data) / in_sr
    audio_tensor = torch.from_numpy(audio_data)
    if audio_tensor.dim() == 1:
        audio_tensor = audio_tensor.unsqueeze(0)
    else:
        audio_tensor = audio_tensor.T
    return (in_sr, audio_tensor), source_duration


def collect_audio_files(path):
    """Return a sorted list of audio file paths found under *path*."""
    files = [
        f for f in glob.glob(os.path.join(path, "*"))
        if os.path.isfile(f) and os.path.splitext(f)[1].lower() in AUDIO_EXTENSIONS
    ]
    if not files:
        raise FileNotFoundError(
            f"No audio files ({', '.join(AUDIO_EXTENSIONS)}) found in {path}"
        )
    return sorted(files)


def run_sweep(
    *,
    model,
    sample_rate,
    sample_size,
    device,
    args,
    sweep_values,
    init_audio_path=None,
    output_dir=None,
):
    """Run the parameter sweep for a single init-audio file (or text-to-audio if None)."""
    conditioning = [{
        "prompt": args.prompt,
        "seconds_total": args.duration,
    }]

    init_audio = None
    source_duration = None
    if init_audio_path:
        init_audio, source_duration = load_init_audio(init_audio_path)
        print(f"  Init audio: {init_audio_path} ({source_duration:.2f}s)")
        if args.match_source_length:
            print(f"  Output will be trimmed to {source_duration:.2f}s")

    base_kwargs = {
        "steps": args.steps,
        "cfg_scale": args.cfg_scale,
        "sigma_min": args.sigma_min,
        "sigma_max": args.sigma_max,
        "init_noise_level": args.init_noise_level,
        "seed": args.seed,
    }

    for i, val in enumerate(sweep_values):
        gen_kwargs = base_kwargs.copy()
        gen_kwargs[args.param] = int(val) if args.param in INT_PARAMS else float(val)

        print(f"  [{i + 1}/{args.n}] {args.param} = {gen_kwargs[args.param]}")

        gen_call_kwargs = dict(
            steps=gen_kwargs["steps"],
            cfg_scale=gen_kwargs["cfg_scale"],
            conditioning=conditioning,
            sample_size=sample_size,
            sigma_min=gen_kwargs["sigma_min"],
            sigma_max=gen_kwargs["sigma_max"],
            sampler_type=args.sampler_type,
            seed=gen_kwargs["seed"],
            device=device,
        )
        if init_audio is not None:
            gen_call_kwargs["init_audio"] = init_audio
            gen_call_kwargs["init_noise_level"] = gen_kwargs["init_noise_level"]

        output = generate_diffusion_cond(model, **gen_call_kwargs)

        trim_to = source_duration if args.match_source_length and source_duration else None
        output = postprocess_output(output, sample_rate, target_duration=trim_to)

        init_filename = os.path.basename(init_audio_path) if init_audio_path else None
        filepath = build_output_path(
            prompt=args.prompt,
            input_filename=init_filename,
            steps=gen_kwargs["steps"],
            cfg_scale=gen_kwargs["cfg_scale"],
            seed=gen_kwargs["seed"],
            noise_level=gen_kwargs.get("init_noise_level") if init_audio else None,
            sampler_type=args.sampler_type,
            duration=args.duration,
            model=args.model,
            sweep_param=args.param,
            sweep_value=gen_kwargs[args.param],
            index=i,
            output_dir=output_dir,
        )
        sf.write(filepath, output.numpy().T, sample_rate)
        print(f"    -> saved {filepath}")


def main():
    args = parse_args()

    device = get_device()
    model, sample_rate, sample_size, _ = load_model(args.model, device)

    sweep_values = np.linspace(args.start, args.end, args.n)
    if args.param in INT_PARAMS:
        sweep_values = sweep_values.astype(int)

    if args.match_source_length and not args.init_audio:
        print("Warning: --match-source-length has no effect without --init-audio; ignoring.")

    if args.outdir:
        run_output_dir = args.outdir
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"sweep_{args.param}_{timestamp}"
        run_output_dir = os.path.join(OUTPUT_DIR, folder_name)
    os.makedirs(run_output_dir, exist_ok=True)

    # Resolve --init-audio to a list of individual file paths (or [None] for text-to-audio).
    if args.init_audio and os.path.isdir(args.init_audio):
        audio_paths = collect_audio_files(args.init_audio)
        print(f"Mode: audio-to-audio BATCH ({len(audio_paths)} files in {args.init_audio})")
    elif args.init_audio:
        audio_paths = [args.init_audio]
        print("Mode: audio-to-audio")
    else:
        audio_paths = [None]
        print("Mode: text-to-audio")

    print(f"Output: {run_output_dir}")
    print(f"Sweeping '{args.param}' over {args.n} values: "
          f"{sweep_values[0]} -> {sweep_values[-1]}")
    print("=" * 60)

    for file_idx, audio_path in enumerate(audio_paths):
        if len(audio_paths) > 1:
            print(f"\n[File {file_idx + 1}/{len(audio_paths)}] "
                  f"{os.path.basename(audio_path)}")
            print("-" * 60)

        run_sweep(
            model=model,
            sample_rate=sample_rate,
            sample_size=sample_size,
            device=device,
            args=args,
            sweep_values=sweep_values,
            init_audio_path=audio_path,
            output_dir=run_output_dir,
        )

    total = args.n * len(audio_paths)
    print("=" * 60)
    print(f"Done. {total} files written to {run_output_dir}")


if __name__ == "__main__":
    main()
