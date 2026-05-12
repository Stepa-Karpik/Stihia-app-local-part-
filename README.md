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
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

Frontend: `http://localhost:5173`  
Backend: `http://localhost:8000`

Данные PostgreSQL и Redis пишутся в `./data`, чтобы не занимать `/var/lib/docker` сверх образов.

ASR runtime тяжелый: он тянет Torch/CUDA. Для обычного запуска он выключен, а если нужен Qwen ASR/Whisper внутри backend-образа:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.asr.yml up -d --build
```
