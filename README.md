# localTTS

Повністю локальний Python pipeline для українського дикторського наративу:

```text
текст / бриф
   ↓
Ollama + Gemma 4
   ↓
NarrationPlan (text + tts_text + pause_after_ms)
   ↓
Silero V5 CIS (ukr_roman)
   ↓
48 kHz mono WAV
```

## Що робить MVP

- `edit` — перетворює готовий український матеріал на природний дикторський текст без додавання нових фактів;
- `generate` — створює наратив із короткого брифу;
- Gemma 4 повертає валідований JSON plan через Ollama Structured Outputs;
- окремо зберігаються `text` для людини та `tts_text` для синтезатора;
- для кожного сегмента задається `pause_after_ms`;
- Silero генерує український голос локально;
- сегменти та паузи об'єднуються у WAV без залежності від FFmpeg;
- є режим `--no-llm`, який працює без Ollama.

## 1. Підготовка Ollama

Переконайтеся, що Ollama встановлена і сервер працює:

```bash
ollama serve
```

Завантажте модель:

```bash
ollama pull gemma4:12b
```

Для меншого використання пам'яті можна спробувати:

```bash
ollama pull gemma4:e4b
```

## 2. Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
```

Перевірка GPU у PyTorch:

```bash
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

## 3. Перший запуск

Відредагувати готовий текст і створити аудіо:

```bash
localtts \
  --input examples/input_uk.txt \
  --mode edit \
  --seconds 60 \
  --output output/narration.wav
```

Результат:

```text
output/plan.json
output/narration.wav
```

`plan.json` можна переглянути перед TTS:

```json
{
  "title": "Український наратив",
  "language": "uk-UA",
  "segments": [
    {
      "text": "...",
      "tts_text": "...",
      "pause_after_ms": 450
    }
  ]
}
```

## 4. Створення тексту з брифу

```bash
localtts \
  --text "Вступ до заняття про застосування ШІ в аналітичній діяльності. Аудиторія — офіцери оперативного рівня." \
  --mode generate \
  --seconds 90 \
  --output output/intro.wav
```

## 5. Спочатку лише текст і паузи

```bash
localtts \
  --input examples/input_uk.txt \
  --mode edit \
  --seconds 90 \
  --plan-only
```

Після перевірки `output/plan.json` у наступній версії буде додано окрему команду `render`, щоб озвучувати вручну відредагований plan без повторного виклику LLM.

## 6. Без Ollama

```bash
localtts \
  --input examples/input_uk.txt \
  --no-llm \
  --output output/narration.wav
```

У цьому режимі текст не переписується: Python лише розбиває його на речення і додає стандартні паузи.

## Голоси Silero

MVP використовує:

```text
model:   v5_cis_base
speaker: ukr_roman
rate:    48000 Hz
```

Альтернативний базовий український голос:

```bash
localtts --input examples/input_uk.txt --speaker ukr_igor
```

> Важливо: Silero V5 CIS не має автоматичного визначення українських наголосів. Офіційна документація рекомендує явно задавати наголоси для слов'янських мов. У MVP ми навмисно не доручаємо Gemma автоматично ставити наголоси, оскільки помилковий наголос гірший за відсутній. Наступний етап — словник наголосів + опційне LLM-assisted доповнення лише для невідомих слів.

## Local-only

Після того як Gemma 4 та Silero model уже завантажені в локальний cache, сам pipeline не потребує хмарного TTS/API. Ollama викликається через локальний endpoint `http://localhost:11434`.

## Наступні кроки

- `localtts render plan.json` без повторної генерації;
- словник українських наголосів та pronunciation overrides;
- профілі `lecture`, `documentary`, `briefing`, `promo`;
- автоматичний loudness normalization через FFmpeg (`-16 LUFS`);
- background music ducking;
- експорт SRT/VTT таймінгів;
- інтеграція з відеопайплайном.

## Джерела API

- Ollama Structured Outputs: https://docs.ollama.com/capabilities/structured-outputs
- Ollama Gemma 4: https://ollama.com/library/gemma4
- Silero Models: https://github.com/snakers4/silero-models
