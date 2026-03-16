"""Web fallback для загрузки больших файлов."""

from __future__ import annotations

from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse

from app.celery_app import celery_app
from app.config import get_settings
from app.fallback_upload import (
    build_uploaded_file_path,
    consume_upload_token,
    get_upload_token_payload,
)
from app.validators import SUPPORTED_EXTENSIONS

app = FastAPI(title="Meeting Analyzer Upload")


def _render_upload_page(token: str, original_file_name: str, file_size: int) -> str:
    return f"""<!doctype html>
<html lang="ru">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Загрузка большой записи</title>
    <style>
      body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background: linear-gradient(135deg, #f6f8fb 0%, #e6edf7 100%);
        color: #162033;
        margin: 0;
        padding: 24px;
      }}
      .card {{
        max-width: 640px;
        margin: 40px auto;
        background: #ffffff;
        border-radius: 20px;
        padding: 32px;
        box-shadow: 0 20px 60px rgba(22, 32, 51, 0.12);
      }}
      h1 {{
        margin-top: 0;
      }}
      .muted {{
        color: #5c667a;
      }}
      input, button {{
        font: inherit;
      }}
      input[type="file"] {{
        display: block;
        margin: 16px 0 24px;
      }}
      button {{
        border: 0;
        border-radius: 999px;
        padding: 14px 22px;
        background: #1f6feb;
        color: #fff;
        cursor: pointer;
      }}
    </style>
  </head>
  <body>
    <div class="card">
      <h1>Загрузка большой записи</h1>
      <p class="muted">Telegram не дал боту скачать исходный файл. Загрузите запись здесь, и результат вернется в тот же Telegram-чат.</p>
      <p><strong>Исходный файл:</strong> {original_file_name}</p>
      <p><strong>Размер по данным Telegram:</strong> {round(file_size / (1024 * 1024), 2) if file_size else "неизвестен"} MB</p>
      <form action="/upload/{token}" method="post" enctype="multipart/form-data">
        <input type="file" name="file" accept=".ogg,.mp3,.m4a,.wav" required>
        <button type="submit">Загрузить и обработать</button>
      </form>
    </div>
  </body>
</html>"""


def _render_result_page(title: str, message: str) -> str:
    return f"""<!doctype html>
<html lang="ru">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title}</title>
    <style>
      body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background: #f6f8fb;
        color: #162033;
        margin: 0;
        padding: 24px;
      }}
      .card {{
        max-width: 640px;
        margin: 40px auto;
        background: #ffffff;
        border-radius: 20px;
        padding: 32px;
        box-shadow: 0 20px 60px rgba(22, 32, 51, 0.12);
      }}
    </style>
  </head>
  <body>
    <div class="card">
      <h1>{title}</h1>
      <p>{message}</p>
    </div>
  </body>
</html>"""


@app.get("/upload/{token}", response_class=HTMLResponse)
async def upload_form(token: str) -> HTMLResponse:
    """Отдает форму загрузки по одноразовому токену."""
    payload = get_upload_token_payload(token)
    if payload is None:
        return HTMLResponse(
            _render_result_page("Ссылка недействительна", "Ссылка уже использована или истекла."),
            status_code=404,
        )

    return HTMLResponse(
        _render_upload_page(
            token=token,
            original_file_name=str(payload.get("file_name", "audio")),
            file_size=int(payload.get("file_size", 0)),
        )
    )


@app.post("/upload/{token}", response_class=HTMLResponse)
async def upload_file(token: str, file: UploadFile = File(...)) -> HTMLResponse:
    """Принимает файл из web-формы и ставит его в очередь."""
    payload = get_upload_token_payload(token)
    if payload is None:
        return HTMLResponse(
            _render_result_page("Ссылка недействительна", "Ссылка уже использована или истекла."),
            status_code=404,
        )

    settings = get_settings()
    extension = Path(file.filename or "").suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        return HTMLResponse(
            _render_result_page(
                "Неподдерживаемый формат",
                "Поддерживаются только ogg, mp3, m4a, wav.",
            ),
            status_code=400,
        )

    destination = build_uploaded_file_path(token, file.filename or f"{token}.bin")
    total_size = 0
    with destination.open("wb") as output:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > settings.max_file_size_bytes:
                destination.unlink(missing_ok=True)
                return HTMLResponse(
                    _render_result_page(
                        "Файл слишком большой",
                        f"Максимально допустимый размер: {settings.max_file_size_mb} MB.",
                    ),
                    status_code=400,
                )
            output.write(chunk)

    celery_app.send_task(
        "app.tasks.process_meeting_task",
        args=[
            {
                "chat_id": int(payload["chat_id"]),
                "user_id": int(payload["user_id"]),
                "source_type": "web_upload",
                "files": [
                    {
                        "local_file_path": str(destination),
                        "file_name": destination.name,
                        "mime_type": file.content_type,
                        "size": total_size,
                    }
                ],
            }
        ],
    )
    consume_upload_token(token)

    return HTMLResponse(
        _render_result_page(
            "Файл принят",
            "Загрузка завершена. Результат придет в Telegram после обработки.",
        )
    )


def run_web() -> None:
    """Запускает web-сервис fallback-загрузки."""
    uvicorn.run("app.web_app:app", host="0.0.0.0", port=8080)
