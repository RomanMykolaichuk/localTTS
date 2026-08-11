from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .audio import peak_normalize, render_plan, save_wav
from .narrator import prepare_with_ollama, prepare_without_llm
from .tts import SileroConfig, SileroUkrainianTTS


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="localtts",
        description="Локальний український narration pipeline: Ollama/Gemma 4 + Silero TTS",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="UTF-8 файл із текстом або брифом")
    source.add_argument("--text", help="Текст або бриф безпосередньо в командному рядку")

    parser.add_argument("--mode", choices=["edit", "generate"], default="edit")
    parser.add_argument("--seconds", type=int, help="Бажана тривалість наративу")
    parser.add_argument(
        "--ollama-model",
        default=os.getenv("LOCALTTS_OLLAMA_MODEL", "gemma4:12b"),
    )
    parser.add_argument(
        "--ollama-host",
        default=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
    )
    parser.add_argument("--no-llm", action="store_true", help="Не використовувати Ollama")
    parser.add_argument("--plan-only", action="store_true", help="Створити лише JSON plan")
    parser.add_argument("--plan-out", type=Path, default=Path("output/plan.json"))
    parser.add_argument("--output", type=Path, default=Path("output/narration.wav"))

    parser.add_argument("--speaker", default="ukr_roman")
    parser.add_argument("--silero-model", default="v5_cis_base")
    parser.add_argument("--sample-rate", type=int, choices=[8000, 24000, 48000], default=48000)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--no-normalize", action="store_true")
    return parser


def _read_source(args: argparse.Namespace) -> str:
    if args.input:
        return args.input.read_text(encoding="utf-8")
    return args.text


def main() -> None:
    args = _parser().parse_args()
    source = _read_source(args).strip()
    if not source:
        raise SystemExit("Вхідний текст порожній.")

    if args.no_llm:
        plan = prepare_without_llm(source)
    else:
        plan = prepare_with_ollama(
            source,
            model=args.ollama_model,
            host=args.ollama_host,
            mode=args.mode,
            target_seconds=args.seconds,
        )

    args.plan_out.parent.mkdir(parents=True, exist_ok=True)
    args.plan_out.write_text(
        json.dumps(plan.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Plan: {args.plan_out} ({len(plan.segments)} segments)")

    if args.plan_only:
        return

    config = SileroConfig(
        model_id=args.silero_model,
        speaker=args.speaker,
        sample_rate=args.sample_rate,
        device=args.device,
    )
    engine = SileroUkrainianTTS(config)
    audio = render_plan(plan, engine)
    if not args.no_normalize:
        audio = peak_normalize(audio)
    output = save_wav(args.output, audio, args.sample_rate)
    duration = audio.numel() / args.sample_rate
    print(f"Audio: {output} | {duration:.1f} s | {args.sample_rate} Hz | {engine.device}")
