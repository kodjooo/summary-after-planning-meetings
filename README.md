# AI Meeting Assistant Bot

Telegram-бот принимает голосовые сообщения и аудиофайлы встреч, транскрибирует их через `whisper-1`, анализирует через OpenAI Responses API и возвращает пользователю структурированный протокол встречи.

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

## Переменные окружения

Основные параметры описаны в `.env.example`.

- `TELEGRAM_BOT_TOKEN` — токен бота от `@BotFather`.
- `OPENAI_API_KEY` — API-ключ OpenAI.
- `OPENAI_ANALYSIS_MODEL` — модель анализа через Responses API.
- `OPENAI_REASONING_EFFORT` — уровень рассуждения модели: `low`, `medium`, `high`.
- `REDIS_URL` — адрес Redis внутри Docker Compose.

## Что умеет MVP

- Принимать `voice`, `audio`, `document`.
- Поддерживать `ogg`, `mp3`, `m4a`, `wav`.
- Объединять несколько подряд голосовых сообщений пользователя в одну обработку.
- Конвертировать аудио через `ffmpeg`.
- Отправлять статусы обработки и итоговый протокол встречи.
- При длинном ответе отправлять краткое сообщение и полный `.txt`-файл.

## Деплой на удалённый сервер

1. Установить Docker Engine и Docker Compose Plugin.
2. Склонировать репозиторий на сервер.
3. Создать `.env` по образцу `.env.example` и заполнить секреты.
4. Выполнить `docker compose up --build -d`.
5. Проверять логи командами `docker compose logs -f bot` и `docker compose logs -f worker`.
