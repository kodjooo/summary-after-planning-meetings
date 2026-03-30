# AI Meeting Assistant Bot

Telegram-бот принимает голосовые сообщения и аудиофайлы встреч, транскрибирует их через `whisper-1`, анализирует через OpenAI Responses API и возвращает пользователю краткое резюме встречи и Excel-таблицу с задачами.

## Запуск

Проект запускается только через Docker Desktop.

1. Заполните значения в `.env`.
2. Соберите и запустите стек:

```bash
docker compose up --build
```

Сервисы:
- `bot` — long polling Telegram-бота.
- `worker` — обработка очереди Celery.
- `redis` — брокер и backend для очереди и буфера голосовых сообщений.
- `web` — fallback-загрузка больших файлов через браузер.

## Переменные окружения

Основные параметры описаны в `.env.example`.

- `TELEGRAM_BOT_TOKEN` — токен бота от `@BotFather`.
- `OPENAI_API_KEY` — API-ключ OpenAI.
- `OPENAI_ANALYSIS_MODEL` — модель анализа через Responses API.
- `OPENAI_REASONING_EFFORT` — уровень рассуждения модели: `low`, `medium`, `high`.
- `MAX_FILE_SIZE_MB` — максимальный размер входного файла, который бот примет в обработку.
- `OPENAI_TRANSCRIPTION_MAX_FILE_SIZE_MB` — безопасный размер части аудио перед отправкой в Whisper.
- `WEB_BASE_URL` — публичный адрес web fallback-загрузки больших файлов.
- `REDIS_URL` — адрес Redis внутри Docker Compose.

## Что умеет MVP

- Принимать `voice`, `audio`, `document`.
- Поддерживать `ogg`, `mp3`, `m4a`, `wav`, `aac`.
- Сразу запускать обработку после отправки голосового сообщения без дополнительного ожидания.
- Конвертировать аудио через `ffmpeg`.
- Для слишком больших Telegram-файлов отдавать одноразовую web-ссылку на резервную загрузку.
- Отправлять статусы обработки, краткое резюме встречи и Excel-файл с таблицей задач.

## Деплой на удалённый сервер

1. Установить Docker Engine и Docker Compose Plugin.
2. Склонировать репозиторий на сервер:

```bash
git clone https://github.com/kodjooo/summary-after-planning-meetings.git
cd summary-after-planning-meetings
```

3. Создать `.env` по образцу `.env.example` и заполнить обязательные значения:

```env
TELEGRAM_BOT_TOKEN=...
OPENAI_API_KEY=...
OPENAI_ANALYSIS_MODEL=gpt-5-mini-2025-08-07
OPENAI_REASONING_EFFORT=low
REDIS_URL=redis://redis:6379/0
WEB_BASE_URL=https://your-public-upload-url
UPLOAD_TOKEN_TTL_SECONDS=3600
TEMP_DIR=/tmp/meeting-assistant
LOG_LEVEL=INFO
MAX_FILE_SIZE_MB=100
OPENAI_TRANSCRIPTION_MAX_FILE_SIZE_MB=24
TRANSCRIPT_CHUNK_SIZE=40000
BOT_STATUS_POLLING_TIMEOUT=30
```

4. Запустить стек:

```bash
docker compose up --build -d
```

5. Проверить, что сервисы поднялись:

```bash
docker compose ps
docker compose logs -f bot worker web
```

6. Если нет root-доступа и нельзя открыть публичный порт для `web`, поднять временный туннель через `cloudflared`:

```bash
cd ~
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
chmod +x cloudflared
nohup ./cloudflared tunnel --url http://localhost:8080 > cloudflared.log 2>&1 &
tail -n 30 ~/cloudflared.log
```

7. Взять из лога URL вида `https://...trycloudflare.com`, прописать его в `.env` как `WEB_BASE_URL`, затем перезапустить контейнеры:

```bash
docker compose down
docker compose up --build -d
```

8. Для обновления проекта на сервере использовать:

```bash
git pull
docker compose down
docker compose up --build -d
```

9. Для диагностики:

```bash
docker compose logs -f bot
docker compose logs -f worker
docker compose logs -f web
```
