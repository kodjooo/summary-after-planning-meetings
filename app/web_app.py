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
      .file-picker {{
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 180px;
        margin: 20px 0 24px;
        padding: 24px;
        border: 2px dashed #9db7dd;
        border-radius: 18px;
        background: #f7fbff;
        color: #24436f;
        text-align: center;
        cursor: pointer;
      }}
      .file-picker:hover {{
        background: #eef6ff;
      }}
      .file-picker input[type="file"] {{
        display: none;
      }}
      button {{
        border: 0;
        border-radius: 999px;
        min-width: 260px;
        min-height: 56px;
        padding: 14px 28px;
        background: #1f6feb;
        color: #fff;
        cursor: pointer;
        transition: opacity 0.2s ease;
      }}
      button:disabled {{
        opacity: 0.7;
        cursor: progress;
      }}
      .file-name {{
        margin-top: 12px;
        color: #5c667a;
      }}
      .status {{
        margin-top: 18px;
        padding: 14px 16px;
        border-radius: 14px;
        background: #f3f6fb;
        color: #3e4d66;
        display: none;
      }}
      .status.visible {{
        display: block;
      }}
      .status.success {{
        background: #e7f7ee;
        color: #19643d;
      }}
      .status.error {{
        background: #fdecec;
        color: #9f2d2d;
      }}
      .progress {{
        margin-top: 16px;
        height: 12px;
        border-radius: 999px;
        background: #dfe7f3;
        overflow: hidden;
        display: none;
      }}
      .progress.visible {{
        display: block;
      }}
      .progress-bar {{
        width: 0%;
        height: 100%;
        background: linear-gradient(90deg, #1f6feb, #4aa1ff);
        transition: width 0.2s ease;
      }}
    </style>
  </head>
  <body>
    <div class="card">
      <h1>Загрузка большой записи</h1>
      <p class="muted">Telegram не дал боту скачать исходный файл. Загрузите запись здесь, и результат вернется в тот же Telegram-чат.</p>
      <p><strong>Исходный файл:</strong> {original_file_name}</p>
      <p><strong>Размер по данным Telegram:</strong> {round(file_size / (1024 * 1024), 2) if file_size else "неизвестен"} MB</p>
      <form id="upload-form" action="/upload/{token}" method="post" enctype="multipart/form-data">
        <label class="file-picker" for="file-input">
          <div>
            <strong>Нажмите, чтобы выбрать файл</strong><br>
            <span class="muted">Поддерживаются ogg, mp3, m4a, wav, aac</span>
            <div id="file-name" class="file-name">Файл не выбран</div>
          </div>
          <input id="file-input" type="file" name="file" accept=".ogg,.mp3,.m4a,.wav,.aac" required>
        </label>
        <button id="submit-button" type="submit">Загрузить и обработать</button>
        <div id="status-box" class="status"></div>
        <div id="progress" class="progress">
          <div id="progress-bar" class="progress-bar"></div>
        </div>
      </form>
      <script>
        const form = document.getElementById("upload-form");
        const fileInput = document.getElementById("file-input");
        const fileName = document.getElementById("file-name");
        const submitButton = document.getElementById("submit-button");
        const statusBox = document.getElementById("status-box");
        const progress = document.getElementById("progress");
        const progressBar = document.getElementById("progress-bar");

        const setStatus = (message, kind = "") => {{
          statusBox.textContent = message;
          statusBox.className = `status visible ${{
            kind ? kind : ""
          }}`.trim();
        }};

        fileInput.addEventListener("change", () => {{
          const selected = fileInput.files && fileInput.files[0];
          fileName.textContent = selected ? `Выбран файл: ${{selected.name}}` : "Файл не выбран";
          if (selected) {{
            setStatus("Файл выбран. Можно загружать.");
          }}
        }});

        form.addEventListener("submit", async (event) => {{
          event.preventDefault();
          if (!fileInput.files || !fileInput.files[0]) {{
            setStatus("Сначала выберите файл для загрузки.", "error");
            return;
          }}

          submitButton.disabled = true;
          submitButton.textContent = "Загружаю...";
          progress.classList.add("visible");
          progressBar.style.width = "0%";
          setStatus("Идет загрузка файла. Не закрывайте страницу.");

          const xhr = new XMLHttpRequest();
          xhr.open("POST", form.action);
          xhr.upload.addEventListener("progress", (progressEvent) => {{
            if (!progressEvent.lengthComputable) {{
              return;
            }}
            const percent = Math.round((progressEvent.loaded / progressEvent.total) * 100);
            progressBar.style.width = `${{percent}}%`;
            setStatus(`Идет загрузка файла: ${{percent}}%.`);
          }});

          xhr.addEventListener("load", () => {{
            submitButton.disabled = false;
            submitButton.textContent = "Загрузить и обработать";
            progressBar.style.width = "100%";
            if (xhr.status >= 200 && xhr.status < 300) {{
              setStatus("Файл успешно загружен. Результат придет в Telegram.", "success");
              fileInput.disabled = true;
              return;
            }}
            setStatus("Загрузка не удалась. Попробуйте еще раз.", "error");
          }});

          xhr.addEventListener("error", () => {{
            submitButton.disabled = false;
            submitButton.textContent = "Загрузить и обработать";
            setStatus("Не удалось отправить файл. Проверьте соединение и попробуйте снова.", "error");
          }});

          const formData = new FormData(form);
          xhr.send(formData);
        }});
      </script>
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
                "Поддерживаются только ogg, mp3, m4a, wav, aac.",
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
