import argparse
import soundfile as sf
from stable_audio_tools.inference.generation import generate_diffusion_cond
from output_naming import build_output_path
from audio_utils import MODEL_REPO_MAP, get_device, load_model, postprocess_output

parser = argparse.ArgumentParser(description="Quick test generation")
parser.add_argument("--model", type=str, default="stable-audio-open-small",
                    choices=list(MODEL_REPO_MAP.keys()),
                    help="Which model to use (default: stable-audio-open-small)")
args = parser.parse_args()

device = get_device()
model, sample_rate, sample_size, _ = load_model(args.model, device)

conditioning = [{
    "prompt": "dubstep bass growls",
    "seconds_start": 0,
    "seconds_total": 11,
}]

output = generate_diffusion_cond(
    model,
    steps=10,
    cfg_scale=2,
    conditioning=conditioning,
    sample_size=sample_size,
    sigma_min=0.3,
    sigma_max=500,
    sampler_type="dpmpp-3m-sde",
    device=device,
)

output = postprocess_output(output, sample_rate)

out_path = build_output_path(
    prompt=conditioning[0]["prompt"],
    steps=10,
    cfg_scale=2,
    sampler_type="dpmpp-3m-sde",
    duration=conditioning[0]["seconds_total"],
    model=args.model,
)
sf.write(out_path, output.numpy().T, sample_rate)
print(f"Saved {out_path}")
