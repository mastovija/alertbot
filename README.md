# AlertBot

Bot de Telegram para recordatorios y alertas inteligentes.
Escríbele en lenguaje natural y te avisará cuando toque.

## Tecnologías

- **FastAPI** + **SQLModel** — API y base de datos
- **PostgreSQL** — almacenamiento de usuarios y alertas
- **Redis** + **Celery** — scheduler de tareas en background
- **Claude API** — interpretación de lenguaje natural
- **python-telegram-bot** — integración con Telegram

## Setup

1. Copia `.env.example` a `.env` y rellena las variables
2. Levanta la infraestructura: `docker compose up -d`
3. Crea las tablas: `python -m app.db.create_tables`

## Desarrollo

Necesitas cuatro terminales:

Terminal 1 — Infraestructura

    docker compose up -d

Terminal 2 — Bot

    python -m app.main

Terminal 3 — Celery Worker

    celery -A app.tasks.scheduler worker --loglevel=info

Terminal 4 — Celery Beat

    celery -A app.tasks.scheduler beat --loglevel=info