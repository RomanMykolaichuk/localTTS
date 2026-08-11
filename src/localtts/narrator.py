from __future__ import annotations

import re
from typing import Literal

from .models import NarrationPlan, NarrationSegment

NarrationMode = Literal["edit", "generate"]

_SYSTEM_PROMPT = """Ти редактор українського дикторського тексту для навчальних відео.
Поверни лише дані, що відповідають переданій JSON Schema.

Правила:
1. Пиши природною сучасною українською мовою, придатною для спокійного професійного озвучення.
2. Не використовуй Markdown, спискові маркери, SSML або службові пояснення всередині text/tts_text.
3. Розбивай наратив на короткі сегменти: зазвичай 1–2 речення, бажано до 350 символів.
4. text — нормальний читабельний текст для людини.
5. tts_text — той самий зміст, але оптимізований для TTS: розгорни неоднозначні скорочення, числа,
   відсотки, математичні та технічні позначення так, як їх має вимовити диктор.
6. Не змінюй власні назви та факти без потреби.
7. pause_after_ms задає паузу ПІСЛЯ сегмента:
   220–350 мс — короткий логічний перехід;
   400–650 мс — завершення думки/абзацу;
   700–1000 мс — зміна смислового блоку;
   останній сегмент — 0 мс.
8. Не додавай фонетичні знаки наголосу. Наголоси будуть окремим етапом пайплайна.
"""


def _target_hint(target_seconds: int | None) -> str:
    if not target_seconds:
        return "Тривалість не задана: збережи зміст без зайвого розширення."
    target_words = round(target_seconds * 2.15)
    return (
        f"Цільова тривалість: приблизно {target_seconds} секунд. "
        f"Орієнтир: близько {target_words} слів, допускається відхилення близько 10%."
    )


def prepare_with_ollama(
    source: str,
    *,
    model: str = "gemma4:12b",
    host: str = "http://localhost:11434",
    mode: NarrationMode = "edit",
    target_seconds: int | None = None,
) -> NarrationPlan:
    """Create a validated narration plan with a local Ollama model."""

    if mode == "edit":
        task = (
            "Відредагуй наданий матеріал у дикторський текст. Збережи всі суттєві факти; "
            "не вигадуй нових фактів і не доповнюй зміст зовнішніми знаннями."
        )
    else:
        task = (
            "На основі наданого брифу створи цілісний дикторський текст. "
            "Не вигадуй точних дат, цифр, назв документів або цитат, якщо їх немає у брифі."
        )

    prompt = f"""{task}
{_target_hint(target_seconds)}

МАТЕРІАЛ / БРИФ:
{source.strip()}
"""

    try:
        from ollama import Client

        client = Client(host=host)
        response = client.chat(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            format=NarrationPlan.model_json_schema(),
            options={"temperature": 0.25},
            think=False,
            stream=False,
        )
        plan = NarrationPlan.model_validate_json(response.message.content)
    except Exception as exc:
        raise RuntimeError(
            f"Не вдалося отримати narration plan від Ollama ({model} @ {host}). "
            "Перевірте `ollama serve` та `ollama pull <model>`."
        ) from exc

    if plan.segments:
        plan.segments[-1].pause_after_ms = 0
    return plan


def prepare_without_llm(source: str) -> NarrationPlan:
    """Deterministic fallback: sentence splitting and fixed pauses, no Ollama required."""

    segments: list[NarrationSegment] = []
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", source) if p.strip()]

    for paragraph in paragraphs:
        sentences = [
            s.strip()
            for s in re.split(r"(?<=[.!?…])\s+", paragraph)
            if s.strip()
        ]
        if not sentences:
            sentences = [paragraph]

        for index, sentence in enumerate(sentences):
            is_last_in_paragraph = index == len(sentences) - 1
            pause = 600 if is_last_in_paragraph else 320
            segments.append(
                NarrationSegment(
                    text=sentence,
                    tts_text=sentence,
                    pause_after_ms=pause,
                )
            )

    if not segments:
        raise ValueError("Вхідний текст порожній.")

    segments[-1].pause_after_ms = 0
    return NarrationPlan(segments=segments)
