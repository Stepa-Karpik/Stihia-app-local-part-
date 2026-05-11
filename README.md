# Стихия

Локальная часть поэтической IDE: редактор стихов, версии, голосовой ввод, локальные ИИ-модели и очередь синхронизации с отдельным Telegram bot server.

## Структура

```text
backend/   FastAPI API
frontend/  React/Vite интерфейс
models/    локальные модели, не попадают в git
```

## Модели

Сами модели не хранятся в репозитории. Положи их в `models/` с именами из `models/README.md`.

`Qwen3-ASR-1.7B` можно подключить volume-путем из `~/Qwen3-ASR-1.7B`.

## Запуск

```bash
cp .env.example .env
docker compose up --build
```

Frontend: `http://localhost:5173`  
Backend: `http://localhost:8000`
