from __future__ import annotations

import wave
from pathlib import Path

import numpy as np
import torch

from .models import NarrationPlan
from .tts import SileroUkrainianTTS


def render_plan(plan: NarrationPlan, engine: SileroUkrainianTTS) -> torch.Tensor:
    chunks: list[torch.Tensor] = []
    sample_rate = engine.config.sample_rate

    for segment in plan.segments:
        chunks.append(engine.synthesize(segment.tts_text))
        if segment.pause_after_ms > 0:
            silence_samples = round(sample_rate * segment.pause_after_ms / 1000)
            chunks.append(torch.zeros(silence_samples, dtype=torch.float32))

    if not chunks:
        raise ValueError("Narration plan не містить сегментів.")
    return torch.cat(chunks)


def peak_normalize(audio: torch.Tensor, target_peak: float = 0.95) -> torch.Tensor:
    peak = float(audio.abs().max()) if audio.numel() else 0.0
    if peak <= 0.0:
        return audio
    gain = min(target_peak / peak, 4.0)
    return (audio * gain).clamp(-1.0, 1.0)


def save_wav(path: str | Path, audio: torch.Tensor, sample_rate: int) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    pcm = audio.detach().to("cpu", dtype=torch.float32).clamp(-1.0, 1.0).numpy()
    pcm16 = (pcm * 32767.0).astype(np.int16)

    with wave.open(str(output), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm16.tobytes())
    return output
