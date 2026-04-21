import os
import argparse
import numpy as np
import torch
import soundfile as sf
from stable_audio_tools.inference.generation import generate_diffusion_cond
from output_naming import build_output_path
from audio_utils import MODEL_REPO_MAP, get_device, load_model, postprocess_output


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate multiple audio outputs sweeping a parameter linearly."
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
                        help="Path to an audio file for audio-to-audio mode. "
                             "If omitted, runs text-to-audio.")
    parser.add_argument("--init_noise_level", type=float, default=0.3,
                        help="Init noise level for audio-to-audio (default: 0.3; "
                             "used when not sweeping 'init_noise_level')")
    parser.add_argument("--seed", type=int, default=-1,
                        help="Random seed (-1 for random; used when not sweeping 'seed')")
    return parser.parse_args()


INT_PARAMS = {"steps", "seed"}


def main():
    args = parse_args()

    device = get_device()
    model, sample_rate, sample_size, _ = load_model(args.model, device)

    sweep_values = np.linspace(args.start, args.end, args.n)
    if args.param in INT_PARAMS:
        sweep_values = sweep_values.astype(int)

    conditioning = [{
        "prompt": args.prompt,
        # "seconds_start": 0,  # removed in small model
        "seconds_total": args.duration,
    }]

    init_audio = None
    if args.init_audio:
        audio_data, in_sr = sf.read(args.init_audio, dtype="float32")
        audio_tensor = torch.from_numpy(audio_data)
        if audio_tensor.dim() == 1:
            audio_tensor = audio_tensor.unsqueeze(0)
        else:
            audio_tensor = audio_tensor.T
        init_audio = (in_sr, audio_tensor)
        print(f"Mode: audio-to-audio (init_audio: {args.init_audio})")
    else:
        print("Mode: text-to-audio")

    base_kwargs = {
        "steps": args.steps,
        "cfg_scale": args.cfg_scale,
        "sigma_min": args.sigma_min,
        "sigma_max": args.sigma_max,
        "init_noise_level": args.init_noise_level,
        "seed": args.seed,
    }

    print(f"Sweeping '{args.param}' over {args.n} values: "
          f"{sweep_values[0]} -> {sweep_values[-1]}")
    print("-" * 60)

    for i, val in enumerate(sweep_values):
        gen_kwargs = base_kwargs.copy()
        gen_kwargs[args.param] = int(val) if args.param in INT_PARAMS else float(val)

        print(f"[{i + 1}/{args.n}] {args.param} = {gen_kwargs[args.param]}")

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

        output = postprocess_output(output, sample_rate)

        init_filename = os.path.basename(args.init_audio) if args.init_audio else None
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
        )
        sf.write(filepath, output.numpy().T, sample_rate)
        print(f"  -> saved {filepath}")

    print("-" * 60)
    print(f"Done. {args.n} files written to Audio/output/")


if __name__ == "__main__":
    main()
