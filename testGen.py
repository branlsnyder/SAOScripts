import argparse
import torch
import soundfile as sf
from einops import rearrange
from stable_audio_tools import get_pretrained_model
from stable_audio_tools.inference.generation import generate_diffusion_cond
from output_naming import build_output_path

MODEL_REPO_MAP = {
    "stable-audio-open-small": "stabilityai/stable-audio-open-small",
    "stable-audio-open": "stabilityai/stable-audio-open-1.0",
}

parser = argparse.ArgumentParser(description="Quick test generation")
parser.add_argument("--model", type=str, default="stable-audio-open-small",
                    choices=list(MODEL_REPO_MAP.keys()),
                    help="Which model to use (default: stable-audio-open-small)")
args = parser.parse_args()

device = "cuda" if torch.cuda.is_available() else "cpu"

model_repo = MODEL_REPO_MAP[args.model]
print(f"Loading model {model_repo}...")
model, model_config = get_pretrained_model(model_repo)
sample_rate = model_config["sample_rate"]
sample_size = model_config["sample_size"]

model = model.to(device)

conditioning = [{
    "prompt": "dubstep bass growls",
    "seconds_start": 0,
    "seconds_total": 11
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
    device=device
)

output = rearrange(output, "b d n -> d (b n)")

output = output.to(torch.float32).div(torch.max(torch.abs(output))).clamp(-1, 1).mul(32767).to(torch.int16).cpu()

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
