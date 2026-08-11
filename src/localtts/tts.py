from __future__ import annotations

from dataclasses import dataclass

import torch


@dataclass(slots=True)
class SileroConfig:
    model_id: str = "v5_cis_base"
    speaker: str = "ukr_roman"
    sample_rate: int = 48000
    device: str = "auto"
    hub_language: str = "ru"


class SileroUkrainianTTS:
    """Thin wrapper around Silero V5 CIS Ukrainian speakers."""

    def __init__(self, config: SileroConfig):
        self.config = config
        self.device = self._resolve_device(config.device)
        self.model, _ = torch.hub.load(
            repo_or_dir="snakers4/silero-models",
            model="silero_tts",
            language=config.hub_language,
            speaker=config.model_id,
            trust_repo=True,
        )
        self.model.to(self.device)

    @staticmethod
    def _resolve_device(requested: str) -> torch.device:
        if requested == "auto":
            return torch.device("cuda" if torch.cuda.is_available() else "cpu")
        if requested == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("Запитано CUDA, але torch.cuda.is_available() == False.")
        return torch.device(requested)

    def synthesize(self, text: str) -> torch.Tensor:
        with torch.inference_mode():
            audio = self.model.apply_tts(
                text=text,
                speaker=self.config.speaker,
                sample_rate=self.config.sample_rate,
            )
        if not isinstance(audio, torch.Tensor):
            audio = torch.as_tensor(audio)
        return audio.detach().to("cpu", dtype=torch.float32).flatten()
