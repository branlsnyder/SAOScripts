"""
Shared utilities for model loading and audio post-processing.
"""

import torch
from einops import rearrange
from stable_audio_tools import get_pretrained_model

MODEL_REPO_MAP = {
    "stable-audio-open-small": "stabilityai/stable-audio-open-small",
    "stable-audio-open": "stabilityai/stable-audio-open-1.0",
}


def get_device() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"


def load_model(model_name: str, device: str | None = None):
    """
    Load a Stable Audio model by short name, move to device, and apply
    the pretransform float32 fix needed by the small model.

    Returns (model, sample_rate, sample_size, max_duration).
    """
    if device is None:
        device = get_device()

    repo = MODEL_REPO_MAP[model_name]
    print(f"Loading model {repo}…")
    model, model_config = get_pretrained_model(repo)
    sample_rate = model_config["sample_rate"]
    sample_size = model_config["sample_size"]
    max_duration = sample_size / sample_rate
    model = model.to(device)

    if model.pretransform is not None:
        model.pretransform.model_half = False
        model.pretransform.model.to(torch.float32)

    print(f"Model loaded — sample rate: {sample_rate}, max duration: {max_duration:.2f}s")
    return model, sample_rate, sample_size, max_duration


def postprocess_output(
    output: torch.Tensor,
    sample_rate: int,
    target_duration: float | None = None,
) -> torch.Tensor:
    """
    Rearrange raw model output, peak-normalize to int16, and optionally
    trim to *target_duration* seconds.
    """
    output = rearrange(output, "b d n -> d (b n)")
    output = (
        output.to(torch.float32)
        .div(torch.max(torch.abs(output)))
        .clamp(-1, 1)
        .mul(32767)
        .to(torch.int16)
        .cpu()
    )

    if target_duration is not None:
        target_samples = int(target_duration * sample_rate)
        if output.shape[-1] > target_samples:
            output = output[..., :target_samples]

    return output
