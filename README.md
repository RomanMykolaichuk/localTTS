# localTTS

Повністю локальний Python pipeline для українського дикторського наративу:

```text
текст / бриф
   ↓
Ollama + gemma4:latest
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
- `gemma4:latest` повертає валідований JSON plan через Ollama Structured Outputs;
- окремо зберігаються `text` для людини та `tts_text` для синтезатора;
- для кожного сегмента задається `pause_after_ms`;
- Silero генерує український голос локально;
- сегменти та паузи об'єднуються у WAV без залежності від FFmpeg;
- є режим `--no-llm`, який працює без Ollama;
- готовий `plan.json` можна рендерити повторно без запуску Gemma.

За замовчуванням CLI використовує:

```text
Ollama model: gemma4:latest
Silero model: v5_cis_base
Speaker:      ukr_roman
Sample rate:  48000 Hz
```

Модель можна перевизначити через `--ollama-model` або змінну середовища `LOCALTTS_OLLAMA_MODEL`.

---

# Послідовність перевірки і генерації

## 1. Отримати актуальну гілку

```bash
git fetch origin
git checkout agent/local-ollama-silero-pipeline
git pull
```

## 2. Перевірити Ollama

Версія:

```bash
ollama --version
```

Перелік локальних моделей:

```bash
ollama list
```

У списку має бути:

```text
gemma4:latest
```

Якщо моделі немає:

```bash
ollama pull gemma4:latest
```

## 3. Перевірити, що Ollama server працює

У більшості інсталяцій Ollama service вже працює у фоні. Перевірка:

```bash
curl http://localhost:11434/api/tags
```

Якщо сервер не запущений:

```bash
ollama serve
```

Якщо `ollama serve` повідомляє, що порт `11434` уже зайнятий, це зазвичай означає, що Ollama вже працює як service.

## 4. Smoke test gemma4:latest

```bash
ollama run gemma4:latest "Відповідай українською одним реченням: тест локальної моделі успішний."
```

Після цього можна перевірити API:

```bash
curl http://localhost:11434/api/generate \
  -d '{
    "model": "gemma4:latest",
    "prompt": "Напиши одне коротке речення українською.",
    "stream": false
  }'
```

## 5. Створити Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
```

Перевірити CLI:

```bash
localtts --help
```

## 6. Перевірити Python package

```bash
python -m compileall src tests
python -m pytest -q
```

## 7. Перевірити PyTorch і GPU

```bash
python -c "import torch; print('torch=', torch.__version__); print('cuda=', torch.cuda.is_available()); print('device=', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

Якщо CUDA недоступна, pipeline все одно може працювати через CPU:

```bash
--device cpu
```

## 8. Перевірити pipeline без LLM

Цей крок перевіряє Python + Silero окремо від Ollama:

```bash
localtts \
  --input examples/input_uk.txt \
  --no-llm \
  --device auto \
  --output output/test_no_llm.wav
```

Очікуваний результат:

```text
output/plan.json
output/test_no_llm.wav
```

## 9. Перевірити тільки Gemma і план наративу

Без запуску TTS:

```bash
localtts \
  --input examples/input_uk.txt \
  --mode edit \
  --seconds 60 \
  --plan-only \
  --plan-out output/test_plan.json
```

CLI автоматично використає:

```text
gemma4:latest
```

Явне задання моделі, якщо потрібно:

```bash
localtts \
  --input examples/input_uk.txt \
  --mode edit \
  --seconds 60 \
  --ollama-model gemma4:latest \
  --plan-only \
  --plan-out output/test_plan.json
```

Переглянути результат:

```bash
cat output/test_plan.json
```

Очікувана структура:

```json
{
  "title": "Український наратив",
  "language": "uk-UA",
  "segments": [
    {
      "text": "Текст для читання людиною.",
      "tts_text": "Текст, підготовлений для синтезатора.",
      "pause_after_ms": 450
    }
  ]
}
```

## 10. Рендер готового plan через Silero

Після перевірки або ручного редагування JSON:

```bash
localtts \
  --plan-in output/test_plan.json \
  --device auto \
  --output output/test_narration.wav
```

Цей запуск НЕ викликає Ollama повторно.

## 11. Повний цикл одним запуском

```bash
localtts \
  --input examples/input_uk.txt \
  --mode edit \
  --seconds 60 \
  --device auto \
  --output output/narration.wav
```

Результат:

```text
output/plan.json
output/narration.wav
```

## 12. Генерація наративу з короткого брифу

```bash
localtts \
  --text "Створи вступ до заняття про застосування штучного інтелекту в аналітичній діяльності. Аудиторія — офіцери оперативного рівня. Стиль — спокійний навчальний наратив." \
  --mode generate \
  --seconds 90 \
  --output output/intro.wav
```

## 13. Використання окремого example file

У репозиторії є:

```text
examples/demo_narration_uk.txt
examples/demo_plan_uk.json
```

Перевірка Gemma:

```bash
localtts \
  --input examples/demo_narration_uk.txt \
  --mode edit \
  --seconds 60 \
  --plan-only \
  --plan-out output/demo_generated_plan.json
```

Перевірка Silero без Gemma:

```bash
localtts \
  --plan-in examples/demo_plan_uk.json \
  --device auto \
  --output output/demo_from_plan.wav
```

Повний цикл:

```bash
localtts \
  --input examples/demo_narration_uk.txt \
  --mode edit \
  --seconds 60 \
  --device auto \
  --output output/demo_full.wav
```

---

# Корисні параметри

## Інша Ollama-модель

```bash
localtts --input text.txt --ollama-model gemma4:latest
```

Або:

```bash
export LOCALTTS_OLLAMA_MODEL=gemma4:latest
```

## Інший український голос

```bash
localtts \
  --input examples/input_uk.txt \
  --speaker ukr_igor
```

## Примусово CUDA

```bash
localtts \
  --input examples/input_uk.txt \
  --device cuda
```

## Примусово CPU

```bash
localtts \
  --input examples/input_uk.txt \
  --device cpu
```

---

# Голоси Silero

MVP використовує:

```text
model:   v5_cis_base
speaker: ukr_roman
rate:    48000 Hz
```

Альтернативний базовий український голос:

```text
ukr_igor
```

> Важливо: Silero V5 CIS не має автоматичного визначення українських наголосів. У MVP Gemma не ставить наголоси автоматично, оскільки неправильно поставлений наголос може погіршити результат. Наступний етап — окремий pronunciation/stress dictionary.

# Local-only

Після завантаження `gemma4:latest` в Ollama та кешування Silero-моделі pipeline може працювати локально без хмарного TTS/API. Ollama викликається через локальний endpoint:

```text
http://localhost:11434
```

# Наступні кроки

- словник українських наголосів та pronunciation overrides;
- профілі `lecture`, `documentary`, `briefing`, `promo`;
- loudness normalization через FFmpeg (`-16 LUFS`);
- background music ducking;
- експорт SRT/VTT таймінгів;
- інтеграція з відеопайплайном.

# Джерела API

- Ollama Structured Outputs: https://docs.ollama.com/capabilities/structured-outputs
- Ollama Gemma 4: https://ollama.com/library/gemma4
- Silero Models: https://github.com/snakers4/silero-models
