import torch
import soundfile as sf
from einops import rearrange
from stable_audio_tools import get_pretrained_model
from stable_audio_tools.inference.generation import generate_diffusion_cond

device = "cuda" if torch.cuda.is_available() else "cpu"

model, model_config = get_pretrained_model("stabilityai/stable-audio-open-small")
sample_rate = model_config["sample_rate"]
sample_size = model_config["sample_size"]

model = model.to(device)
if model.pretransform is not None:
	model.pretransform.model_half = False
	model.pretransform.model.to(torch.float32)

conditioning = [{
	"prompt": "128 BPM tech house drum loop",
}]

output = generate_diffusion_cond(
	model,
	conditioning=conditioning,
	sample_size=sample_size,
	device=device
)

output = rearrange(output, "b d n -> d (b n)")

output = output.to(torch.float32).div(torch.max(torch.abs(output))).clamp(-1, 1).cpu()
sf.write("output.wav", output.numpy().T, sample_rate)